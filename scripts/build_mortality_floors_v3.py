"""Mortality floors v3: the pre-registration packet's three data-side
blockers answered from bytes, with the floor rebuilt on the declared
universe under a pinned death-ascertainment convention.

REPORTED ANCHOR, NOT A GATE RUN. Like ``mortality_floors_v1`` and
``mortality_floors_v2``, this reads no gate, changes no gate and
ratifies nothing; it is committed evidence pinned by a reproduction
test. It SUPERSEDES ``runs/mortality_floors_v2.json`` as the floor
basis a future differential-mortality gate ceremony (issue #74 Phase
B) would derive pre-registered thresholds from, and RETAINS v1 and v2
byte-for-byte as the pre-lock record. ``gates.yaml`` is untouched by
this artifact and by this script.

The mortality gate's pre-registration packet orders the ceremony:
answer R1, R6 and R7 first, because they change the data the floor is
built on. v2 answered R2 (100 seeds), R3 (Kish counts) and R5 (anchor
margins) and INHERITED v1's ascertainment and censoring conventions
unchanged. This artifact answers the three blockers as the packet's
"Evidence required" lists state them, each from the bytes of the PSID
release rather than from prose:

R1 -- the weight universe.
    (1) The per-wave weight-variable resolution table -- every wave's
    variable, its label, the fallback pattern that resolved it, its
    SPSS storage format and its codebook target population -- is
    COMMITTED in the artifact rather than derived at read time.
    (2) Per gated cell, the share of weighted exposure and of
    unweighted deaths carried by each series, plus the sample-stratum
    composition (SRC / SEO / 1997 immigrant / 2017 immigrant) by era.
    (3) The floor is rebuilt at 100 seeds on the declared 1997+
    universe AND on the all-window universe under every convention
    below, so the referee sees the tolerance movement cell by cell.
    (4) v1's ``exposure_construction.biennial_caveats[1]`` is
    WITHDRAWN with the measurement that refutes it: its premise (older
    decades run higher) fails in half the cells outright, and its
    mechanism (an offset against the undercount) cannot operate
    because the pre-1997 series carry 0.096% of the weighted
    denominator -- the pre-1997 weights are family-scale decimals
    (SPSS F4.1 / F7.3) while the 1997+ cross-section weight is a
    population-scaled integer (F6.0 / F5.0).

R6 -- the death-ascertainment convention.
    The pinned convention assigns each of the 200 range-coded deaths
    of span <= 2 years the year ``floor((lo + hi) / 2)`` and scores it
    with the exact-year machinery unchanged. The 93 wide codes and 12
    NA-year deaths are published as a sensitivity band whose lower end
    scores them as survival (v1/v2's treatment) and whose upper end
    assigns them at the exact deaths' measured in-frame ascertainment
    rate, respecting each range where one exists. A packet-literal
    upper end that ignores the ranges is published as well. The
    movement of every gated cell's hazard and tolerance between the
    conventions is MEASURED at 100 seeds, replacing the packet's
    +3.9% / 0.038-log estimate.

R7 -- the censoring convention.
    ``governance.censoring`` names the rule (quoted from the v1
    builder's docstring), the non-informative-nonresponse assumption
    it rests on, the PSID/NCHS ratios as the evidence against it, and
    the attrition-hazard-by-age evidence R4 shares: per band x sex,
    the wave-to-wave attrition hazard against the death hazard and the
    share of attriters with a later known death.

Run from the repository root with the PSID individual file staged::

    .venv/bin/python scripts/build_mortality_floors_v3.py

It needs no populace-fit (real-vs-real / real-vs-external only).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_mortality_floors as v1b  # noqa: E402
import build_mortality_floors_v2 as v2b  # noqa: E402

from populace_dynamics.data import deaths, panels, psid  # noqa: E402
from populace_dynamics.harness import panel as hpanel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT / "runs" / "mortality_floors_v3.json"
V1_PATH = ROOT / "runs" / "mortality_floors_v1.json"
V2_PATH = ROOT / "runs" / "mortality_floors_v2.json"
M6_PATH = ROOT / "runs" / "m6_holdout_floors_v4.json"
NCHS_PATH = ROOT / "data" / "external" / "nchs_life_tables_2023.json"
GATES_PATH = ROOT / "gates.yaml"
BUILDER_V1_PATH = ROOT / "scripts" / "build_mortality_floors.py"
BUILDER_V2_PATH = ROOT / "scripts" / "build_mortality_floors_v2.py"
ARTIFACT_SCHEMA_VERSION = "mortality_floors.v3"

FLOOR_SEEDS: tuple[int, ...] = v2b.FLOOR_SEEDS
DECLARED_UNIVERSE_START = v2b.DECLARED_UNIVERSE_START
T_MAX = v2b.T_MAX
MARGIN_K = v2b.MARGIN_K
CELL_ORDER: tuple[str, ...] = v2b.CELL_ORDER

#: A range code ``lo-hi`` is NARROW when ``hi - lo <= NARROW_MAX_SPAN``
#: (the packet's "width <= 2 years": 106 codes at span 1, 94 at span 2).
NARROW_MAX_SPAN = 2

#: The four death-ascertainment conventions the floor is built under.
CONVENTION_SURVIVAL = "survival_v1_v2"
CONVENTION_PINNED = "pinned_narrow_midpoint"
CONVENTION_UPPER_INFORMED = "band_upper_informed"
CONVENTION_UPPER_LITERAL = "band_upper_packet_literal"
CONVENTIONS: tuple[str, ...] = (
    CONVENTION_SURVIVAL,
    CONVENTION_PINNED,
    CONVENTION_UPPER_INFORMED,
    CONVENTION_UPPER_LITERAL,
)
UNIVERSES: dict[str, int | None] = {
    "declared_1997_plus": DECLARED_UNIVERSE_START,
    "all_v1_comparable": None,
}

#: The lines of the v1 builder's module docstring the packet cites for
#: the censoring rule (R7: "build_mortality_floors.py:56-61"), and the
#: lines that hold the whole caveat item (the cited span stops one
#: line short of the item's last line).
CENSORING_RULE_CITED_LINES = (56, 61)
CENSORING_RULE_ITEM_LINES = (57, 62)

#: PSID sample strata by 1968 interview number (``ER30001``, the
#: thousands part of ``person_id``), transcribed from the IND2023ER
#: codebook's weight-variable entries (e.g. ER30019, ER30686, ER33430,
#: ER34651, ER35265): core SRC 1-2930, core SEO 5001-6872, 1997/1999
#: Immigrant 3001-3511, 2017/2019 Immigrant 4001-4851, Latino
#: 7001-9308.
SAMPLE_STRATA: tuple[tuple[str, int, int], ...] = (
    ("core_SRC", 1, 2930),
    ("core_SEO", 5001, 6872),
    ("immigrant_1997_1999", 3001, 3511),
    ("immigrant_2017_2019", 4001, 4851),
    ("latino_1990_1995", 7001, 9308),
)

#: Target population and storage scale of each weight series, transcribed
#: from the IND2023ER codebook (sha256 pinned in the artifact). The
#: ``codebook_entry`` names the variable whose entry the text is taken
#: from; the ``nonzero_range`` is the codebook's own value range.
WEIGHT_SERIES_DOCUMENTATION: dict[str, dict[str, Any]] = {
    "INDIVIDUAL WEIGHT": {
        "waves": "1968-1989 (annual)",
        "codebook_entry": "ER30019 (1968), ER30042 (1969), ER30641 (1989)",
        "storage_format": "F4.1",
        "nonzero_range": ".1 - 99.9",
        "target_population": (
            "the 1968 core sample (SRC + SEO) only: 'nonzero only for "
            "sample members associated with a [wave] response family'; "
            "zero for 'Immigrant or Latino samples (ER30001=3001-3511, "
            "4001-4851, 7001-9308)', nonsample individuals "
            "(ER30002=170-228) and persons born or moved in after the "
            "wave. Family-level weight from 1968 carried to persons; "
            "the 1969 entry notes it was 'recalculated for 1969, taking "
            "account of the heavier nonresponse losses suffered in that "
            "year, including mortality'."
        ),
        "scale": "family-weight scale (decimal, max 99.9); NOT population-scaled",
        "longitudinal": True,
    },
    "CORE IND WEIGHT": {
        "waves": "1990-1992 (annual)",
        "codebook_entry": "ER30686 (1990)",
        "storage_format": "F7.3",
        "nonzero_range": ".001 - 999.999",
        "target_population": (
            "'to be used only for analysis of the core sample'; nonzero "
            "'only for sample members associated with a 1990 core sample "
            "family'; zero for 'Immigrant or Latino samples individual', "
            "main-family nonresponse, nonsample individuals and persons "
            "born or moved in after the wave. The Latino sample's own "
            "weight (LATINO IND WEIGHT, ER30687) and the COMBINED IND "
            "WEIGHT (ER30688) exist for 1990-1995 and are NOT resolved "
            "by the fallback order."
        ),
        "scale": "1989 core weight updated (decimal, max 131.9 in the frame); NOT population-scaled",
        "longitudinal": True,
    },
    "CORE INDIVIDUAL LONGITUDINAL WEIGHT": {
        "waves": "1993-1996 (annual)",
        "codebook_entry": "ER30864 (1993)",
        "storage_format": "F7.3",
        "nonzero_range": ".001 - 999.999 (documented range .282-109.916)",
        "target_population": (
            "'to be used only for analysis of the core sample'; nonzero "
            "'only for sample members associated with a 1993 core sample "
            "response family'; a LONGITUDINAL weight recalculated for "
            "Release 3 ('PSID Revised Longitudinal Weights 1993-2005'). "
            "Latino-sample individuals carry zero."
        ),
        "scale": "revised longitudinal weight (decimal, max 109.916); NOT population-scaled",
        "longitudinal": True,
    },
    "CORE/IMM INDIVIDUAL CROSS-SECTION WT": {
        "waves": "1997-2023 (1997 annual step, then biennial)",
        "codebook_entry": (
            "ER33438 (1997), ER33547 (1999), ER34651 (2017), ER34864 "
            "(2019), ER35065 (2021), ER35265 (2023)"
        ),
        "storage_format": "F6.0 (1997), F5.0 (1999-2023)",
        "nonzero_range": "62 - 118,766 (1997); 32 - 91,004 (1999); 402 - 57,330 (2023)",
        "target_population": (
            "the core sample combined with the 1997/1999 Immigrant "
            "refresher ('Core-Immigrant Individual Cross-sectional "
            "Weight', 'Cross-sectional Analysis of PSID Data and "
            "Cross-sectional Weights 1997-2005'); zero for 'not response' "
            "in the wave. From 2017 the entry reads 'updated for all "
            "individuals in 2017 including the Immigrant 2017 sample' "
            "and from 2019/2021 'core-immigrant 97/99/17/19', so the "
            "2017/2019 Immigrant refresher (ER30001=4001-4851) enters the "
            "target population at the 2017 wave. Latino-sample "
            "individuals (ER30001=7001-9308) carry zero in every wave. A "
            "separate CORE/IMM INDIVIDUAL LONGITUDINAL WT (ER33430 ...) "
            "exists for the same waves and is NOT resolved by the "
            "fallback order."
        ),
        "scale": "population-scaled integer (person represents ~weight US residents)",
        "longitudinal": False,
    },
}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _sha_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(cwd: Path) -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd)
            .decode()
            .strip()
        )
    except Exception:
        return None


def _psid_ind_dir() -> Path:
    return psid._resolve_data_dir(None) / psid.PRODUCTS["ind2023er"][0]


def _log_ratio(a: float, b: float) -> float | None:
    return float(math.log(a / b)) if a > 0 and b > 0 else None


def _hazard_map(slices: pd.DataFrame) -> dict[str, float]:
    return {k: v["psid_m"] for k, v in v1b.weighted_hazards(slices).items()}


def _window(slices: pd.DataFrame, start_year_min: int | None) -> pd.DataFrame:
    if start_year_min is None:
        return slices
    return slices[slices.start_wave >= start_year_min]


# --------------------------------------------------------------------------
# R1 -- the weight universe, from the release's own bytes
# --------------------------------------------------------------------------
_FORMAT_RE = re.compile(r"(ER\d+[A-Z]?)\s+\((F[0-9]+\.[0-9]+)\)")


def parse_sps_formats(sps_path: Path) -> dict[str, str]:
    """Variable -> SPSS display format (``F4.1`` ...) from the setup file.

    The ``FORMATS`` block is the only place ``NAME (Fw.d)`` pairs occur
    in a PSID setup file; the width/decimals pair is the storage scale
    of the series (a weight stored ``F4.1`` cannot exceed 999.9, one
    stored ``F6.0`` is an integer up to 999,999).
    """
    text = sps_path.read_text(errors="replace")
    return {name: fmt for name, fmt in _FORMAT_RE.findall(text)}


def weight_resolution_table() -> list[dict[str, Any]]:
    """Per wave: the weight variable the fallback order resolves.

    Replays ``panels._resolve_concepts`` for the ``weight`` concept
    against the real ``ind2023er`` label space and records, for every
    wave, the variable name, its label, the pattern (and its rank in
    the fallback tuple) that matched it, its SPSS column span and
    display format, and the canonical series name. Committed in the
    artifact so a referee reads the resolution rather than re-deriving
    it.
    """
    sps_path = psid.product_sps_path("ind2023er")
    labels = psid.parse_sps_labels(sps_path)
    layout = psid.parse_sps_layout(sps_path).set_index("name")
    formats = parse_sps_formats(sps_path)
    patterns = panels.DEMOGRAPHIC_CONCEPTS["weight"]
    resolved: dict[int, tuple[str, int, str]] = {}
    for rank, pattern in enumerate(patterns):
        for year, name in panels.wave_variables(labels, pattern).items():
            resolved.setdefault(year, (name, rank, pattern))
    rows: list[dict[str, Any]] = []
    for year in sorted(resolved):
        name, rank, pattern = resolved[year]
        rows.append(
            {
                "wave": int(year),
                "variable": name,
                "label": labels[name],
                "series": v2b._canonical_series(labels[name]),
                "fallback_rank": rank,
                "fallback_pattern": pattern,
                "sps_columns": [
                    int(layout.loc[name, "start"]),
                    int(layout.loc[name, "end"]),
                ],
                "sps_format": formats.get(
                    name, f"F{int(layout.loc[name, 'width'])}.0"
                ),
                "sps_format_source": (
                    "FORMATS block"
                    if name in formats
                    else "implicit integer: no FORMATS entry, DATA LIST width"
                ),
            }
        )
    return rows


def weight_series_summary(
    table: list[dict[str, Any]], slices: pd.DataFrame
) -> dict[str, Any]:
    """Per canonical series: waves, variables, formats, measured scale."""
    df = slices.copy()
    series_by_wave = {r["wave"]: r["series"] for r in table}
    df["series"] = df.start_wave.map(series_by_wave)
    out: dict[str, Any] = {}
    for series in dict.fromkeys(r["series"] for r in table):
        rows = [r for r in table if r["series"] == series]
        grp = df[df.series == series]
        doc = WEIGHT_SERIES_DOCUMENTATION[series]
        out[series] = {
            "waves_resolved": [rows[0]["wave"], rows[-1]["wave"]],
            "n_waves_resolved": len(rows),
            "variables": [rows[0]["variable"], rows[-1]["variable"]],
            "sps_formats": sorted({r["sps_format"] for r in rows}),
            "fallback_rank": rows[0]["fallback_rank"],
            "fallback_pattern": rows[0]["fallback_pattern"],
            "codebook": doc,
            "measured_in_frame": {
                "start_waves_present": (
                    [
                        int(grp.start_wave.min()),
                        int(grp.start_wave.max()),
                    ]
                    if len(grp)
                    else None
                ),
                "n_slices": int(len(grp)),
                "mean_slice_weight": (
                    float(grp.weight.mean()) if len(grp) else None
                ),
                "max_slice_weight": (
                    float(grp.weight.max()) if len(grp) else None
                ),
            },
        }
    return out


def per_cell_series_shares(
    slices: pd.DataFrame, series_by_wave: dict[int, str]
) -> dict[str, Any]:
    """Per gated cell: exposure and death shares by weight series."""
    df = slices.copy()
    df["series"] = df.start_wave.map(series_by_wave)
    df["we"] = df.weight * df.exposure
    out: dict[str, Any] = {}
    for key in CELL_ORDER:
        band, sex = key.split("|")
        cell = df[(df.band == band) & (df.sex == sex)]
        total_we = float(cell.we.sum())
        total_d = float(cell.death.sum())
        by_series: dict[str, Any] = {}
        for series in dict.fromkeys(
            series_by_wave[w] for w in sorted(series_by_wave)
        ):
            grp = cell[cell.series == series]
            by_series[series] = {
                "n_slices": int(len(grp)),
                "weighted_exposure_py": float(grp.we.sum()),
                "share_of_weighted_exposure": (
                    float(grp.we.sum() / total_we) if total_we else None
                ),
                "deaths_unwt": int(round(float(grp.death.sum()))),
                "share_of_unweighted_deaths": (
                    float(grp.death.sum() / total_d) if total_d else None
                ),
            }
        pre = cell[cell.start_wave < DECLARED_UNIVERSE_START]
        out[key] = {
            "weighted_exposure_py": total_we,
            "deaths_unwt": int(round(total_d)),
            "by_series": by_series,
            "pre_1997_share_of_weighted_exposure": (
                float(pre.we.sum() / total_we) if total_we else None
            ),
            "pre_1997_share_of_unweighted_deaths": (
                float(pre.death.sum() / total_d) if total_d else None
            ),
        }
    return out


def _stratum_of(person_id: np.ndarray) -> np.ndarray:
    interview = person_id // 1000
    conditions = [
        (interview >= lo) & (interview <= hi) for _, lo, hi in SAMPLE_STRATA
    ]
    names = [name for name, _, _ in SAMPLE_STRATA]
    return np.select(conditions, names, default="other")


def sample_stratum_shares(slices: pd.DataFrame) -> dict[str, Any]:
    """Weighted exposure / death / person shares by sample stratum and era.

    The era cut points are the two target-population changes the
    codebook records inside the resolved series: 1997 (the Immigrant
    refresher enters with the cross-section weight) and 2017 (the
    2017/2019 Immigrant refresher enters).
    """
    df = slices.copy()
    df["stratum"] = _stratum_of(df.person_id.to_numpy(np.int64))
    df["we"] = df.weight * df.exposure
    eras = (
        ("pre_1997", None, 1996),
        ("1997_2015", 1997, 2015),
        ("2017_plus", 2017, None),
    )
    out: dict[str, Any] = {
        "strata": [
            {"name": n, "er30001_range": [lo, hi]}
            for n, lo, hi in SAMPLE_STRATA
        ],
        "by_era": {},
    }
    for era, lo, hi in eras:
        mask = pd.Series(True, index=df.index)
        if lo is not None:
            mask &= df.start_wave >= lo
        if hi is not None:
            mask &= df.start_wave <= hi
        grp = df[mask]
        total_we = float(grp.we.sum())
        total_d = float(grp.death.sum())
        strata: dict[str, Any] = {}
        for name, sub in grp.groupby("stratum", observed=True):
            strata[str(name)] = {
                "n_persons": int(sub.person_id.nunique()),
                "n_slices": int(len(sub)),
                "share_of_weighted_exposure": float(sub.we.sum() / total_we),
                "deaths_unwt": int(round(float(sub.death.sum()))),
                "share_of_unweighted_deaths": (
                    float(sub.death.sum() / total_d) if total_d else None
                ),
            }
        out["by_era"][era] = {
            "start_waves": [lo, hi],
            "n_slices": int(len(grp)),
            "by_stratum": strata,
        }
    return out


def withdrawal_of_v1_caveat(
    slices: pd.DataFrame,
    v1_artifact: dict[str, Any],
    v2_artifact: dict[str, Any],
    weights: dict[str, Any],
    series_summary: dict[str, Any],
    equivalence: dict[str, Any],
    anchor_all: dict[str, Any],
) -> dict[str, Any]:
    """The written withdrawal of ``biennial_caveats[1]``, with its refutation.

    Three measurements, each of which alone defeats the caveat:

    * PREMISE. "Older decades bias PSID upward." Measured within each
      window (each weighted by its own series), the pre-1997 hazard is
      LOWER than the 1997+ hazard in half the cells, including both 85+
      cells; the premise is not even uniformly true.
    * MECHANISM. Whatever the pre-1997 hazard is, it enters the pooled
      statistic in proportion to its weighted exposure, and that is
      0.096% of the denominator because the pre-1997 series are
      family-scale decimals while the 1997+ weight is a
      population-scaled integer. A bias riding on 0.096% of the
      denominator offsets nothing.
    * CONSEQUENCE. ``|ln(m_all / m_1997+)|`` is below 4e-4 in every
      cell, against an undercount of 0.15-1.02 log units per cell; the
      claimed offset is at most 0.3% of the smallest undercount.
    """
    pre = _hazard_map(slices[slices.start_wave < DECLARED_UNIVERSE_START])
    post = _hazard_map(slices[slices.start_wave >= DECLARED_UNIVERSE_START])
    premise: dict[str, Any] = {}
    higher = 0
    lower = 0
    for key in CELL_ORDER:
        lr = _log_ratio(pre.get(key, 0.0), post.get(key, 0.0))
        premise[key] = {
            "m_pre_1997_within_window": float(pre.get(key, 0.0)),
            "m_1997_plus_within_window": float(post.get(key, 0.0)),
            "ln_pre_over_post": lr,
            "older_decades_run_higher": (lr is not None and lr > 0),
        }
        if lr is not None:
            higher += lr > 0
            lower += lr < 0
    undercount = {
        key: (
            float(abs(math.log(cell["ratio"]))) if cell.get("ratio") else None
        )
        for key, cell in anchor_all["by_band_sex"].items()
    }
    defined_undercount = [v for v in undercount.values() if v is not None]
    pre_share = weights["pre_1997"]["share_of_weighted_exposure"]
    max_equiv = equivalence["max_abs_log_ratio"]
    return {
        "withdrawn_text": v1_artifact["exposure_construction"][
            "biennial_caveats"
        ][1],
        "withdrawn_from": "runs/mortality_floors_v1.json exposure_construction.biennial_caveats[1]",
        "v2_withdrawal_carried": v2_artifact["exposure_construction"][
            "withdrawn_v1_caveat"
        ]["why_withdrawn"],
        "premise_measured": {
            "statistic": (
                "ln(m_pre_1997 / m_1997_plus) per cell, each window's "
                "hazard weighted by its own series"
            ),
            "per_cell": premise,
            "n_cells_older_decades_higher": int(higher),
            "n_cells_older_decades_lower": int(lower),
            "reading": (
                "the caveat's premise -- that pooling older decades "
                "raises the PSID rate -- holds in only "
                f"{higher} of 14 cells and fails in {lower}, including "
                "both 85+ cells where the pre-1997 hazard is about 30% "
                "LOWER than the 1997+ hazard"
            ),
        },
        "mechanism_measured": {
            "pre_1997_share_of_weighted_exposure": float(pre_share),
            "pre_1997_share_of_unweighted_deaths": float(
                weights["pre_1997"]["share_of_unweighted_deaths"]
            ),
            "mean_slice_weight_pre_1997": float(
                weights["pre_1997"]["mean_slice_weight"]
            ),
            "mean_slice_weight_1997_plus": float(
                weights["from_1997"]["mean_slice_weight"]
            ),
            "storage_formats": {
                name: s["sps_formats"] for name, s in series_summary.items()
            },
            "reading": (
                "the pre-1997 series are stored as family-scale decimals "
                "(F4.1 / F7.3, max 131.9 in the frame) and the 1997+ "
                "cross-section weight as a population-scaled integer "
                "(F6.0 / F5.0, max 78,934), so pooling them is not a "
                "weighted average of two periods: the pre-1997 slices "
                f"carry {100 * pre_share:.4f}% of the weighted "
                "denominator and cannot move the pooled rate"
            ),
        },
        "consequence_measured": {
            "max_abs_ln_m_all_over_m_1997_plus": float(max_equiv),
            "undercount_abs_ln_ratio_per_cell_all_window": undercount,
            "min_undercount_abs_ln_ratio": (
                float(min(defined_undercount)) if defined_undercount else None
            ),
            "claimed_offset_as_share_of_min_undercount": (
                float(max_equiv / min(defined_undercount))
                if defined_undercount
                else None
            ),
            "reading": (
                "the pooled 'all' rate differs from the 1997+ rate by at "
                f"most {max_equiv:.6f} log units in any cell, against an "
                f"undercount of at least {min(defined_undercount):.3f} "
                "log units; the offset the caveat claims is at most "
                f"{100 * max_equiv / min(defined_undercount):.2f}% of the "
                "smallest undercount"
            ),
        },
        "verdict": (
            "WITHDRAWN. The caveat asserted that pooling older decades "
            "biases the PSID rate upward and so works against the "
            "undercount. Measured from the frame: the premise fails in "
            f"{lower} of 14 cells, the mechanism cannot operate because "
            "the pre-1997 series carry 0.096% of the weighted "
            "denominator, and the pooled rate is the 1997+ rate to "
            "4e-4 log units. Nothing in v3 restates it."
        ),
    }


# --------------------------------------------------------------------------
# R6 -- death ascertainment, from the death file's own codes
# --------------------------------------------------------------------------
def _observed_frame(demo: pd.DataFrame, dr: pd.DataFrame) -> pd.DataFrame:
    """Person-wave observations under the v1 builder's filters."""
    obs = demo[(demo.age <= v1b.MAX_AGE) & (demo.weight > 0)].copy()
    obs["sex"] = obs.person_id.map(dr.set_index("person_id")["sex"])
    obs = obs[obs.sex.isin(v1b.SEXES)].copy()
    return obs


def _grid(demo: pd.DataFrame) -> tuple[list[int], dict[int, int]]:
    grid = sorted(int(w) for w in demo.period.unique())
    return grid, {w: grid[i + 1] for i, w in enumerate(grid[:-1])}


def last_observed(
    obs: pd.DataFrame, next_wave: dict[int, int]
) -> pd.DataFrame:
    """Per person: last observed wave, its next grid wave, age, weight."""
    last = (
        obs.sort_values("period")
        .groupby("person_id")
        .tail(1)
        .set_index("person_id")[["period", "age", "weight", "sex"]]
        .rename(columns={"period": "last_wave"})
    )
    last["next_wave"] = last.last_wave.map(next_wave)
    return last


def assign_narrow_death_years(dr: pd.DataFrame) -> pd.DataFrame:
    """THE PINNED CONVENTION: narrow range codes get ``floor((lo+hi)/2)``.

    A range code ``lo-hi`` with ``hi - lo <= NARROW_MAX_SPAN`` is given
    the death year ``floor((lo + hi) / 2)`` -- ``lo`` for a span-1
    code, ``lo + 1`` for a span-2 code -- and thereafter scored by the
    exact-year machinery unchanged (counted iff the person was observed
    at the start of the grid interval containing that year; the
    death-year slice carries exposure 0.5). Wide codes and NA-year
    deaths are left without a year here and handled by the band.
    """
    out = dr.copy()
    span = (out.death_year_hi - out.death_year_lo).astype("float")
    narrow = (out.death_status == "range") & (span <= NARROW_MAX_SPAN)
    mid = (
        out.death_year_lo.astype("float") + out.death_year_hi.astype("float")
    ) // 2
    out.loc[narrow, "death_year"] = mid[narrow].astype("Int64")
    out["assigned_by_pinned_rule"] = narrow.to_numpy()
    return out


def death_record_classification(
    dr: pd.DataFrame,
    obs: pd.DataFrame,
    last: pd.DataFrame,
    grid: list[int],
    next_wave: dict[int, int],
) -> dict[str, Any]:
    """Every non-exact death record placed against the observation grid."""
    counts = dr.death_status.value_counts().to_dict()
    rng = dr[dr.death_status == "range"].copy()
    rng["lo"] = rng.death_year_lo.astype(int)
    rng["hi"] = rng.death_year_hi.astype(int)
    rng["span"] = rng.hi - rng.lo
    observed_pairs = pd.MultiIndex.from_arrays([obs.person_id, obs.period])
    rng["in_frame"] = rng.person_id.isin(last.index)
    rng["observed_at_lo"] = pd.MultiIndex.from_arrays(
        [rng.person_id, rng.lo]
    ).isin(observed_pairs)
    rng["last_wave"] = rng.person_id.map(last.last_wave)
    rng["lo_is_grid_wave"] = rng.lo.isin(grid)
    rng["hi_is_next_grid_wave_of_lo"] = [
        next_wave.get(lo) == hi for lo, hi in zip(rng.lo, rng.hi, strict=True)
    ]
    rng["last_wave_before_lo"] = rng.in_frame & (rng.last_wave < rng.lo)
    nxt_of_last = rng.last_wave.map(
        lambda w: next_wave.get(int(w)) if pd.notna(w) else np.nan
    )
    rng["range_overlaps_last_interval"] = (
        rng.in_frame
        & nxt_of_last.notna()
        & ~((nxt_of_last <= rng.lo) | (rng.last_wave > rng.hi))
    )
    narrow = rng[rng.span <= NARROW_MAX_SPAN]
    wide = rng[rng.span > NARROW_MAX_SPAN]
    na = dr[dr.death_status == "na_dk"].copy()
    na["in_frame"] = na.person_id.isin(last.index)
    na["last_wave"] = na.person_id.map(last.last_wave)
    na["has_last_interval"] = na.last_wave.map(
        lambda w: pd.notna(w) and int(w) in next_wave
    )

    def _block(d: pd.DataFrame) -> dict[str, Any]:
        return {
            "n": int(len(d)),
            "in_frame": int(d.in_frame.sum()),
            "observed_at_lo": int(d.observed_at_lo.sum()),
            "in_frame_last_wave_before_lo": int(d.last_wave_before_lo.sum()),
            "lo_is_grid_wave": int(d.lo_is_grid_wave.sum()),
            "hi_is_next_grid_wave_of_lo": int(
                d.hi_is_next_grid_wave_of_lo.sum()
            ),
            "range_overlaps_last_observed_interval": int(
                d.range_overlaps_last_interval.sum()
            ),
            "by_sex": {
                str(s): int(n) for s, n in d.sex.value_counts().items()
            },
        }

    return {
        "status_counts": {str(k): int(v) for k, v in counts.items()},
        "range_span_definition": "span = hi - lo (years); narrow = span <= 2",
        "range_span_distribution": {
            str(int(s)): int(n)
            for s, n in rng.span.value_counts().sort_index().items()
        },
        "narrow": _block(narrow),
        "narrow_by_span": {
            str(int(s)): _block(narrow[narrow.span == s])
            for s in sorted(narrow.span.unique())
        },
        "narrow_lo_distribution": {
            str(int(y)): int(n)
            for y, n in narrow.lo.value_counts().sort_index().items()
        },
        "wide": _block(wide),
        "na_year": {
            "n": int(len(na)),
            "in_frame": int(na.in_frame.sum()),
            "in_frame_with_last_interval": int(na.has_last_interval.sum()),
        },
        "frame_filters": (
            "a person is in frame when observed in at least one wave with "
            "sequence number 1-20, age <= 120, weight > 0 and sex "
            "male/female -- the v1 builder's filters"
        ),
        "reading": (
            "a range code's first year is a grid wave in "
            f"{int(narrow.lo_is_grid_wave.sum())} of "
            f"{len(narrow)} narrow codes and its last year is the very "
            f"next grid wave in {int(narrow.hi_is_next_grid_wave_of_lo.sum())}: "
            "the codes record 'last seen at lo, found dead by hi'. Only "
            f"{int(narrow.observed_at_lo.sum())} narrow-coded decedents "
            "were observed at lo under the frame's filters; "
            f"{int(narrow.last_wave_before_lo.sum())} in-frame decedents "
            "were last observed BEFORE lo (died after attrition, "
            "exactly the right-censored case the censoring rule "
            "already loses for exact deaths), and "
            f"{int((~narrow.in_frame).sum())} are not in the frame at all."
        ),
    }


def ascertainment_rates(
    dr_pinned: pd.DataFrame,
    last: pd.DataFrame,
    frame_deaths: int,
    n_exact: int,
) -> dict[str, Any]:
    """The exact deaths' ascertainment rate, measured several ways.

    The packet's 0.483 divides banded ascertained events (3,775) by
    ALL exact decedents (7,816), including the 1,017 never observed
    under the frame's filters and the deaths at ages below 25 that
    carry no band. The rule's rate is the in-frame conditional: of
    exact decedents with a last observed interval, the share whose
    death year falls in it.
    """
    ex = dr_pinned[dr_pinned.death_status == "exact"].set_index("person_id")
    ex = ex.drop(columns=["sex"]).join(last, how="inner")
    ex = ex[ex.next_wave.notna()].copy()
    ex["asc"] = (ex.death_year >= ex.last_wave) & (
        ex.death_year < ex.next_wave
    )
    ex["after"] = ex.death_year >= ex.next_wave
    ex["before"] = ex.death_year < ex.last_wave
    ex["band"] = ex.age.map(v1b._band_of)
    by_band = {
        str(b): {
            "n": int(len(g)),
            "ascertained": int(g.asc.sum()),
            "rate": float(g.asc.mean()),
        }
        for b, g in ex.groupby("band", observed=True)
    }
    recent = ex[ex.last_wave >= DECLARED_UNIVERSE_START]
    two = ex[ex.asc & ((ex.next_wave - ex.last_wave) == 2)]
    second = int((two.death_year == two.last_wave + 1).sum())
    return {
        "packet_rate": {
            "value": float(frame_deaths / n_exact),
            "numerator": int(frame_deaths),
            "denominator": int(n_exact),
            "what_it_divides": (
                "banded (25+) ascertained death events over ALL exact "
                "decedents, including those never in the frame; not a "
                "conditional probability of ascertainment"
            ),
        },
        "in_frame_rate": {
            "value": float(ex.asc.mean()),
            "numerator": int(ex.asc.sum()),
            "denominator": int(len(ex)),
            "what_it_divides": (
                "exact decedents whose death year falls in the grid "
                "interval after their last observed wave, over exact "
                "decedents in the frame with such an interval (all ages)"
            ),
            "death_after_last_interval": int(ex.after.sum()),
            "death_before_last_observed_wave": int(ex.before.sum()),
        },
        "in_frame_rate_last_wave_1997_plus": {
            "value": float(recent.asc.mean()),
            "numerator": int(recent.asc.sum()),
            "denominator": int(len(recent)),
        },
        "by_age_band_at_last_wave": by_band,
        "within_two_year_interval_split": {
            "n_ascertained_in_two_year_intervals": int(len(two)),
            "n_in_first_year": int(len(two) - second),
            "n_in_second_year": second,
            "p_second_year": float(second / len(two)) if len(two) else None,
        },
        "rule_rate_used_by_the_band": float(ex.asc.mean()),
    }


def fractional_death_targets(
    dr: pd.DataFrame,
    last: pd.DataFrame,
    next_wave: dict[int, int],
    *,
    respect_ranges: bool,
    exclude_assigned: pd.Series,
) -> pd.DataFrame:
    """Which non-exact decedents the band's upper end scores, and where.

    ``respect_ranges=True`` (the INFORMED upper end): a wide-coded
    decedent is scored only if their range overlaps the interval after
    their last observed wave, and only the years inside the range are
    feasible; an NA-year decedent in the frame is scored with every
    year of that interval feasible. ``respect_ranges=False`` (the
    PACKET-LITERAL upper end): every in-frame non-exact decedent not
    already assigned by the pinned rule is scored in the interval
    after their last observed wave with every year feasible, ignoring
    what their range says.
    """
    rows: list[dict[str, Any]] = []
    non_exact = dr[dr.death_status.isin(["range", "na_dk"])]
    excluded = (
        non_exact.person_id.map(exclude_assigned)
        .fillna(False)
        .astype(bool)
        .to_numpy()
    )
    non_exact = non_exact[~excluded]
    for rec in non_exact.itertuples(index=False):
        if rec.person_id not in last.index:
            continue
        info = last.loc[rec.person_id]
        w = int(info.last_wave)
        if w not in next_wave:
            continue
        nxt = next_wave[w]
        years = list(range(w, nxt))
        if rec.death_status == "range" and respect_ranges:
            lo, hi = int(rec.death_year_lo), int(rec.death_year_hi)
            years = [y for y in years if lo <= y <= hi]
            if not years:
                continue
        rows.append(
            {
                "person_id": int(rec.person_id),
                "death_status": str(rec.death_status),
                "start_wave": w,
                "next_wave": int(nxt),
                "age_at_start": int(info.age),
                "sex": str(info.sex),
                "feasible_first_year": w in years,
                "feasible_second_year": (w + 1) in years,
            }
        )
    return pd.DataFrame(rows)


def apply_fractional_deaths(
    slices: pd.DataFrame,
    targets: pd.DataFrame,
    r: float,
    p_second_year: float,
) -> pd.DataFrame:
    """Score each target as dying in its interval with probability ``r``.

    Expected-value construction. With probability ``1 - r`` the person
    survives the interval (exposure 1 per slice, no death); with
    probability ``r * p_j`` they die in feasible slice ``j`` (the
    death slice carries exposure 0.5 and one death, a later slice
    nothing). ``p`` splits the death across the two slices of a
    biennial interval by the measured second-year share of exact
    ascertained deaths, renormalised over the feasible slices.
    """
    out = slices.copy()
    if targets.empty:
        return out
    idx = out.set_index(["person_id", "start_wave"]).index
    for t in targets.itertuples(index=False):
        rows = out[idx == (t.person_id, t.start_wave)]
        if rows.empty:
            continue
        ages = sorted(rows.age.unique())
        first_age = t.age_at_start
        if t.feasible_first_year and t.feasible_second_year:
            two_year = (t.next_wave - t.start_wave) == 2
            p0 = (1.0 - p_second_year) if two_year else 1.0
            p1 = p_second_year if two_year else 0.0
        elif t.feasible_first_year:
            p0, p1 = 1.0, 0.0
        else:
            p0, p1 = 0.0, 1.0
        for age in ages:
            mask = (idx == (t.person_id, t.start_wave)) & (out.age == age)
            if age == first_age:
                out.loc[mask, "exposure"] = 1.0 - 0.5 * r * p0
                out.loc[mask, "death"] = r * p0
            elif age == first_age + 1:
                out.loc[mask, "exposure"] = 1.0 - r * p0 - 0.5 * r * p1
                out.loc[mask, "death"] = r * p1
    return out


def build_convention_frames(
    demo: pd.DataFrame, dr: pd.DataFrame
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """The exposure frame under each of the four conventions."""
    grid, next_wave = _grid(demo)
    obs = _observed_frame(demo, dr)
    last = last_observed(obs, next_wave)

    survival = v1b.build_exposure_slices(demo, dr)
    dr_pinned = assign_narrow_death_years(dr)
    pinned = v1b.build_exposure_slices(demo, dr_pinned)

    rates = ascertainment_rates(
        dr_pinned,
        last,
        frame_deaths=int(round(float(survival.death.sum()))),
        n_exact=int((dr.death_status == "exact").sum()),
    )
    r = rates["rule_rate_used_by_the_band"]
    p2 = rates["within_two_year_interval_split"]["p_second_year"]
    assigned = dr_pinned.set_index("person_id")["assigned_by_pinned_rule"]

    targets_informed = fractional_death_targets(
        dr, last, next_wave, respect_ranges=True, exclude_assigned=assigned
    )
    targets_literal = fractional_death_targets(
        dr, last, next_wave, respect_ranges=False, exclude_assigned=assigned
    )
    upper_informed = apply_fractional_deaths(pinned, targets_informed, r, p2)
    upper_literal = apply_fractional_deaths(pinned, targets_literal, r, p2)

    frames = {
        CONVENTION_SURVIVAL: survival,
        CONVENTION_PINNED: pinned,
        CONVENTION_UPPER_INFORMED: upper_informed,
        CONVENTION_UPPER_LITERAL: upper_literal,
    }
    classification = death_record_classification(
        dr, obs, last, grid, next_wave
    )

    def _targets_block(t: pd.DataFrame) -> dict[str, Any]:
        if t.empty:
            return {"n_persons": 0}
        banded = t[t.age_at_start.map(v1b._band_of).notna()]
        return {
            "n_persons": int(len(t)),
            "by_status": {
                str(s): int(n)
                for s, n in t.death_status.value_counts().items()
            },
            "n_with_banded_start_age": int(len(banded)),
            "expected_added_death_events_all_ages": float(r * len(t)),
            "by_start_wave_era": {
                "pre_1997": int(
                    (t.start_wave < DECLARED_UNIVERSE_START).sum()
                ),
                "1997_plus": int(
                    (t.start_wave >= DECLARED_UNIVERSE_START).sum()
                ),
            },
            "persons": (
                [
                    {
                        "person_id": int(x.person_id),
                        "death_status": x.death_status,
                        "start_wave": int(x.start_wave),
                        "next_wave": int(x.next_wave),
                        "age_at_start": int(x.age_at_start),
                        "sex": x.sex,
                        "feasible_years": [
                            y
                            for y, ok in (
                                (int(x.start_wave), x.feasible_first_year),
                                (
                                    int(x.start_wave) + 1,
                                    x.feasible_second_year,
                                ),
                            )
                            if ok and y < int(x.next_wave)
                        ],
                    }
                    for x in t.itertuples(index=False)
                ]
                if len(t) <= 20
                else None
            ),
        }

    added = pinned[
        pinned.person_id.isin(
            dr_pinned[dr_pinned.assigned_by_pinned_rule].person_id
        )
        & (pinned.death > 0)
    ]
    detail = {
        "grid": {"first": grid[0], "last": grid[-1], "n_waves": len(grid)},
        "classification": classification,
        "ascertainment_rates": rates,
        "pinned_rule_effect": {
            "death_events_survival_convention": int(
                round(float(survival.death.sum()))
            ),
            "death_events_pinned_convention": int(
                round(float(pinned.death.sum()))
            ),
            "death_events_added": int(
                round(float(pinned.death.sum() - survival.death.sum()))
            ),
            "added_by_cell": {
                f"{b}|{s}": int(n)
                for (b, s), n in added.groupby(["band", "sex"], observed=True)
                .size()
                .items()
            },
            "added_by_start_wave_era": {
                "pre_1997": int(
                    (added.start_wave < DECLARED_UNIVERSE_START).sum()
                ),
                "1997_plus": int(
                    (added.start_wave >= DECLARED_UNIVERSE_START).sum()
                ),
            },
            "n_slices_survival": int(len(survival)),
            "n_slices_pinned": int(len(pinned)),
        },
        "upper_band_targets": {
            CONVENTION_UPPER_INFORMED: _targets_block(targets_informed),
            CONVENTION_UPPER_LITERAL: _targets_block(targets_literal),
        },
        "expected_death_events_by_convention": {
            name: float(frame.death.sum()) for name, frame in frames.items()
        },
        "expected_death_events_by_convention_declared_universe": {
            name: float(_window(frame, DECLARED_UNIVERSE_START).death.sum())
            for name, frame in frames.items()
        },
    }
    return frames, detail


def within_rule_sensitivity(
    demo: pd.DataFrame, dr: pd.DataFrame, pinned: pd.DataFrame
) -> dict[str, Any]:
    """Assigning narrow codes at ``lo`` or at ``hi`` instead of the midpoint."""
    out: dict[str, Any] = {}
    span = (dr.death_year_hi - dr.death_year_lo).astype("float")
    narrow = (dr.death_status == "range") & (span <= NARROW_MAX_SPAN)
    base = {u: _hazard_map(_window(pinned, s)) for u, s in UNIVERSES.items()}
    for name, column in (
        ("assign_at_lo", "death_year_lo"),
        ("assign_at_hi", "death_year_hi"),
    ):
        alt = dr.copy()
        alt.loc[narrow, "death_year"] = alt.loc[narrow, column].astype("Int64")
        frame = v1b.build_exposure_slices(demo, alt)
        entry: dict[str, Any] = {
            "death_events": int(round(float(frame.death.sum()))),
        }
        for u, s in UNIVERSES.items():
            haz = _hazard_map(_window(frame, s))
            diffs = {
                k: _log_ratio(haz.get(k, 0.0), base[u].get(k, 0.0))
                for k in CELL_ORDER
            }
            defined = [abs(v) for v in diffs.values() if v is not None]
            entry[u] = {
                "ln_m_variant_over_m_pinned_per_cell": diffs,
                "max_abs": float(max(defined)) if defined else None,
            }
        out[name] = entry
    return out


def post_death_observation_note(
    slices: pd.DataFrame, dr: pd.DataFrame
) -> dict[str, Any]:
    """Exact decedents observed after their recorded death year.

    The inherited rule credits every observed wave as exposure, so a
    person whose death year precedes a later observed wave keeps
    contributing exposure after it. Disclosed and measured; the rule
    is not changed here.
    """
    dy = slices.person_id.map(dr.set_index("person_id").death_year).astype(
        "float"
    )
    post = dy.notna() & (slices.start_wave > dy)
    base = {u: _hazard_map(_window(slices, s)) for u, s in UNIVERSES.items()}
    trimmed = slices[~post]
    movement: dict[str, Any] = {}
    for u, s in UNIVERSES.items():
        haz = _hazard_map(_window(trimmed, s))
        diffs = [
            abs(v)
            for v in (
                _log_ratio(haz.get(k, 0.0), base[u].get(k, 0.0))
                for k in CELL_ORDER
            )
            if v is not None
        ]
        movement[u] = float(max(diffs)) if diffs else None
    ex = dr[dr.death_status == "exact"].set_index("person_id")
    persons = slices[post].person_id.unique()
    return {
        "n_exact_decedents_with_post_death_slices": int(len(persons)),
        "n_post_death_slices": int(post.sum()),
        "their_deaths_counted_in_frame": int(
            slices[slices.person_id.isin(persons)].death.sum()
        ),
        "max_abs_ln_movement_if_dropped": movement,
        "convention": (
            "INHERITED and disclosed: post-death observed waves stay "
            "credited as exposure (a PSID death-file year that precedes "
            "a later in-family observation is a record inconsistency the "
            "frame does not adjudicate). Dropping those slices moves no "
            "cell by more than the figure recorded here."
        ),
        "n_exact_decedents_total": int(len(ex)),
    }


# --------------------------------------------------------------------------
# R7 -- censoring: the rule, its assumption, and the evidence against it
# --------------------------------------------------------------------------
def censoring_rule_quote() -> dict[str, Any]:
    lines = BUILDER_V1_PATH.read_text().splitlines()
    c0, c1 = CENSORING_RULE_CITED_LINES
    i0, i1 = CENSORING_RULE_ITEM_LINES
    return {
        "source": "scripts/build_mortality_floors.py module docstring, 'Biennial-panel caveats' item 1",
        "source_sha256": _sha_of_file(BUILDER_V1_PATH),
        "packet_cites_lines": f"{c0}-{c1}",
        "cited_lines_text": [lines[i - 1] for i in range(c0, c1 + 1)],
        "item_lines": f"{i0}-{i1}",
        "rule_quoted": " ".join(
            lines[i - 1].strip() for i in range(i0, i1 + 1)
        ),
        "code_location": (
            "build_exposure_slices: exposure is credited only for a "
            "person-wave observed present (sequence 1-20, age <= 120, "
            "weight > 0) whose grid wave has a successor; a death is "
            "counted iff its year falls in that one interval"
        ),
    }


def person_interval_table(
    obs: pd.DataFrame,
    dr_pinned: pd.DataFrame,
    dr: pd.DataFrame,
    next_wave: dict[int, int],
) -> pd.DataFrame:
    """One row per observed person-wave with a following grid wave.

    Outcome of the interval: ``continues`` (observed at the next grid
    wave), ``death`` (pinned-convention death year in the interval, any
    age), else ``attrit``. For attriters: whether a death is known
    later (exact or range with ``lo`` at or after the next wave, or an
    NA-year death), and whether the person is observed again later.
    """
    pi = obs[["person_id", "period", "age", "weight", "sex"]].copy()
    pi["next_wave"] = pi.period.map(next_wave)
    pi = pi[pi.next_wave.notna()].copy()
    pi["next_wave"] = pi.next_wave.astype(int)
    present = pd.MultiIndex.from_arrays([obs.person_id, obs.period])
    pi["continues"] = pd.MultiIndex.from_arrays(
        [pi.person_id, pi.next_wave]
    ).isin(present)
    dy = pi.person_id.map(dr_pinned.set_index("person_id").death_year).astype(
        "float"
    )
    pi["death"] = ((dy >= pi.period) & (dy < pi.next_wave)).to_numpy()
    pi["attrit"] = (~pi.continues & ~pi.death).to_numpy()
    status = pi.person_id.map(dr.set_index("person_id").death_status)
    lo = pi.person_id.map(dr.set_index("person_id").death_year_lo).astype(
        "float"
    )
    pi["later_known_death"] = (
        pi.attrit
        & (status != "not_deceased")
        & ((lo >= pi.next_wave) | (status == "na_dk"))
    ).to_numpy()
    max_wave = obs.groupby("person_id").period.max()
    pi["returns_later"] = (
        pi.attrit & (pi.person_id.map(max_wave) > pi.next_wave)
    ).to_numpy()
    pi["band"] = pi.age.map(v1b._band_of)
    pi["length"] = pi.next_wave - pi.period
    return pi[pi.band.notna()].reset_index(drop=True)


def attrition_evidence(pi: pd.DataFrame) -> dict[str, Any]:
    """Per band x sex and window: attrition hazard against death hazard."""

    def _table(d: pd.DataFrame) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key in CELL_ORDER:
            band, sex = key.split("|")
            x = d[(d.band == band) & (d.sex == sex)]
            if x.empty:
                out[key] = None
                continue
            w = float(x.weight.sum())
            n_attrit = int(x.attrit.sum())
            death_wt = float((x.weight * x.death).sum() / w)
            attrit_wt = float((x.weight * x.attrit).sum() / w)
            out[key] = {
                "n_person_intervals": int(len(x)),
                "n_deaths": int(x.death.sum()),
                "n_attrit": n_attrit,
                "n_continue": int(x.continues.sum()),
                "death_hazard_per_interval_wt": death_wt,
                "attrition_hazard_per_interval_wt": attrit_wt,
                "death_hazard_per_interval_unwt": float(x.death.mean()),
                "attrition_hazard_per_interval_unwt": float(x.attrit.mean()),
                "attrition_over_death_wt": (
                    float(attrit_wt / death_wt) if death_wt > 0 else None
                ),
                "share_of_attriters_with_later_known_death_unwt": (
                    float(x.later_known_death.sum() / n_attrit)
                    if n_attrit
                    else None
                ),
                "share_of_attriters_observed_again_unwt": (
                    float(x.returns_later.sum() / n_attrit)
                    if n_attrit
                    else None
                ),
                "mean_interval_length_years": float(x.length.mean()),
            }
        return out

    return {
        "unit": (
            "observed person-wave with a following grid wave; outcome "
            "= continues (observed at the next grid wave) / death "
            "(pinned-convention death year in the interval, any age) / "
            "attrit (neither). Hazards are per interval (1 year through "
            "1996, 2 years from 1997), weighted by the start-wave weight"
        ),
        "n_person_intervals_banded": int(len(pi)),
        "totals": {
            "continues": int(pi.continues.sum()),
            "death": int(pi.death.sum()),
            "attrit": int(pi.attrit.sum()),
        },
        "windows": {
            "all": _table(pi),
            "declared_1997_plus": _table(
                pi[pi.period >= DECLARED_UNIVERSE_START]
            ),
            "pre_1997": _table(pi[pi.period < DECLARED_UNIVERSE_START]),
        },
    }


def censoring_governance(
    quote: dict[str, Any],
    anchor_windows: dict[str, Any],
    attrition: dict[str, Any],
) -> dict[str, Any]:
    ratios = {
        w: {
            "min_ratio": a["ratio_summary"]["min_ratio"],
            "max_ratio": a["ratio_summary"]["max_ratio"],
            "median_ratio": a["ratio_summary"]["median_ratio"],
            "n_estimable_cells": a["ratio_summary"]["n_estimable_cells"],
        }
        for w, a in anchor_windows.items()
    }
    declared = attrition["windows"]["declared_1997_plus"]
    eighty_five = {
        k: declared[k]["share_of_attriters_with_later_known_death_unwt"]
        for k in ("85+|male", "85+|female")
    }
    young = declared["25-34|female"][
        "share_of_attriters_with_later_known_death_unwt"
    ]
    return {
        "rule": quote,
        "assumption": (
            "NON-INFORMATIVE NONRESPONSE: conditional on age band and "
            "sex, a person not observed at the next grid wave (and with "
            "no ascertained death in the interval) has the same death "
            "hazard as a person who is observed there. Under it, ending "
            "exposure at the last observed wave and counting only deaths "
            "in the one interval after it is an unbiased hazard."
        ),
        "evidence_against": {
            "psid_over_nchs_ratios": {
                "statistic": (
                    "PSID weighted central death rate over the NCHS 2023 "
                    "period rate, per band x sex; below 1 is the "
                    "undercount. Recomputed here on the v3 pinned "
                    "convention; v1/v2's all-window figures (0.360-0.857, "
                    "median 0.760) are the survival-convention values"
                ),
                "by_window": ratios,
                "reading": (
                    "the panel records roughly three quarters of the "
                    "deaths per person-year the period population "
                    "experiences. Death itself removes people from the "
                    "panel between waves, so nonresponse is informative "
                    "for mortality by construction; the undercount IS the "
                    "measurement of the violation"
                ),
            },
            "attrition_versus_death_by_age_and_sex": {
                "table": attrition,
                "reading": (
                    "on the declared universe the share of attriters "
                    "with a death known later rises from "
                    f"{100 * young:.1f}% at 25-34|female to "
                    f"{100 * eighty_five['85+|male']:.1f}% (male) / "
                    f"{100 * eighty_five['85+|female']:.1f}% (female) at "
                    "85+, and the attrition hazard falls from two "
                    "orders of magnitude above the death hazard at 25-34 "
                    "to below it at 85+. Attrition and death are least "
                    "separable in the oldest stratum -- the R4 evidence"
                ),
            },
        },
        "binds": (
            "the censoring rule binds both sides of every score: the "
            "PSID truth half and any candidate are scored on frames "
            "built with this rule, and no PASS may describe the "
            "censoring as innocuous or the hazard as free of the "
            "undercount"
        ),
    }


# --------------------------------------------------------------------------
# Floors under a convention (fractional deaths allowed)
# --------------------------------------------------------------------------
def _kish_weighted_events(weights: np.ndarray, events: np.ndarray) -> float:
    """Kish effective count of the weighted event total ``(sum wd)^2/sum (wd)^2``."""
    wd = weights * events
    total = float(wd.sum())
    sq = float((wd**2).sum())
    return float(total * total / sq) if sq > 0 else 0.0


def _half_stats(half: pd.DataFrame) -> tuple[dict[str, Any], dict[str, float]]:
    haz = v1b.weighted_hazards(half)
    dead = half[half.death > 0]
    kish: dict[str, float] = {}
    for (band, sex), grp in dead.groupby(["band", "sex"], observed=True):
        kish[v1b._key(band, sex)] = _kish_weighted_events(
            grp.weight.to_numpy(np.float64), grp.death.to_numpy(np.float64)
        )
    return haz, kish


def measure_seed(
    seed: int,
    slices: pd.DataFrame,
    *,
    start_year_min: int | None,
    full: bool = True,
) -> dict[str, Any]:
    """One seed's half-split; v2's cell shape (``full``) or a compact one.

    SPLIT FRAME PIN (v1/v2's convention, load-bearing): the split is
    taken on the FULL slice frame and the window filter applied to each
    side afterwards. Every convention's frame carries the identical
    person set, so seed ``s`` draws the identical person partition
    under every convention and both universes.
    """
    side_a, side_b = hpanel.split_panel_by_person(
        slices, "person_id", fraction=0.5, seed=seed
    )
    n_a = int(side_a.person_id.nunique())
    n_b = int(side_b.person_id.nunique())
    side_a = _window(side_a, start_year_min)
    side_b = _window(side_b, start_year_min)
    haz_a, kish_a = _half_stats(side_a)
    haz_b, kish_b = _half_stats(side_b)
    dead_a = (
        side_a[side_a.death > 0]
        .groupby(["band", "sex"], observed=True)
        .death.sum()
    )
    dead_b = (
        side_b[side_b.death > 0]
        .groupby(["band", "sex"], observed=True)
        .death.sum()
    )

    cells: dict[str, Any] = {}
    for key in CELL_ORDER:
        band, sex = key.split("|")
        a = haz_a.get(key)
        b = haz_b.get(key)
        m_a = a["psid_m"] if a else 0.0
        m_b = b["psid_m"] if b else 0.0
        defined = m_a > 0 and m_b > 0
        cell: dict[str, Any] = {
            "m_a": float(m_a),
            "m_b": float(m_b),
            "n_death_a": int(a["psid_deaths_unwt"]) if a else 0,
            "n_death_b": int(b["psid_deaths_unwt"]) if b else 0,
            "kish_death_a": float(kish_a.get(key, 0.0)),
            "kish_death_b": float(kish_b.get(key, 0.0)),
            "log_ratio_abs": (
                float(abs(np.log(m_a / m_b))) if defined else None
            ),
        }
        if full:
            cell["pct_diff_abs"] = (
                float(abs(m_a - m_b) / m_b * 100.0) if defined else None
            )
        else:
            cell["deaths_expected_a"] = float(dead_a.get((band, sex), 0.0))
            cell["deaths_expected_b"] = float(dead_b.get((band, sex), 0.0))
        cells[key] = cell
    out: dict[str, Any] = {
        "seed": seed,
        "n_persons_side_a": n_a,
        "n_persons_side_b": n_b,
        "cells": cells,
    }
    if full:
        out["hazards_side_a"] = {k: v["psid_m"] for k, v in haz_a.items()}
        out["hazards_side_b"] = {k: v["psid_m"] for k, v in haz_b.items()}
    return out


def pool_floor(
    per_seed: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """v2's pooling, tolerant of the compact cell shape."""
    floors: dict[str, Any] = {}
    stability: dict[str, Any] = {}
    n_seeds = len(per_seed)
    for key in CELL_ORDER:
        ratios = [s["cells"][key]["log_ratio_abs"] for s in per_seed]
        min_deaths = min(
            min(s["cells"][key]["n_death_a"], s["cells"][key]["n_death_b"])
            for s in per_seed
        )
        min_kish = min(
            min(
                s["cells"][key]["kish_death_a"],
                s["cells"][key]["kish_death_b"],
            )
            for s in per_seed
        )
        defined_seeds = sum(v is not None for v in ratios)
        block = None
        if defined_seeds == n_seeds:
            block = v1b._summary([float(v) for v in ratios])
            values = np.asarray(block["values"], dtype=np.float64)
            block["realized_sigma"] = float(np.sqrt((values**2).mean()))
            if all("pct_diff_abs" in s["cells"][key] for s in per_seed):
                block["pct_diff_abs"] = v1b._summary(
                    [float(s["cells"][key]["pct_diff_abs"]) for s in per_seed]
                )
            floors[key] = block
        entry: dict[str, Any] = {
            "defined_seeds": defined_seeds,
            "n_seeds": n_seeds,
            "min_deaths_either_half": int(min_deaths),
            "min_effective_deaths_kish": round(float(min_kish), 3),
            "v1_rule_gate_eligible": bool(
                defined_seeds == n_seeds
                and min_deaths >= v1b.MIN_DEATHS_FOR_GATE
            ),
        }
        if block is not None:
            entry["realized_sigma"] = block["realized_sigma"]
            for k in (2, 3, 4):
                entry[f"tolerance_k{k}"] = v2b._tolerance(
                    block["mean"], block["sd"], k
                )
            entry["tolerance_sigma_units_k3"] = round(
                entry["tolerance_k3"] / block["realized_sigma"], 3
            )
            entry["clears_t_max_at_k3"] = bool(entry["tolerance_k3"] <= T_MAX)
        else:
            entry["clears_t_max_at_k3"] = False
        if defined_seeds < n_seeds:
            entry["report_reason"] = "undefined_on_some_seed"
        elif not entry["clears_t_max_at_k3"]:
            entry["report_reason"] = "tolerance_above_t_max"
        elif min_deaths < v1b.MIN_DEATHS_FOR_GATE:
            entry["report_reason"] = "below_20_deaths_weaker_half"
        else:
            entry["report_reason"] = "clears_t_max_at_k3"
        stability[key] = entry
    return floors, stability


def build_floors(
    frames: dict[str, pd.DataFrame], verbose: bool
) -> dict[str, Any]:
    """100-seed floors for every convention x universe.

    The survival convention is measured with v2's own ``measure_seed``
    (the literal v2 code path) so its floors can be asserted equal to
    the committed v2 bytes; the pinned convention keeps v2's full cell
    shape (the anchor invariants need the per-half hazard vectors); the
    two upper-band conventions use the compact shape.
    """
    out: dict[str, Any] = {}
    for name in CONVENTIONS:
        frame = frames[name]
        out[name] = {}
        for universe, start in UNIVERSES.items():
            started = time.time()
            if name == CONVENTION_SURVIVAL:
                per_seed = [
                    v2b.measure_seed(s, frame, start_year_min=start)
                    for s in FLOOR_SEEDS
                ]
            else:
                per_seed = [
                    measure_seed(
                        s,
                        frame,
                        start_year_min=start,
                        full=(
                            name == CONVENTION_PINNED
                            and universe == "declared_1997_plus"
                        ),
                    )
                    for s in FLOOR_SEEDS
                ]
            floor, stability = pool_floor(per_seed)
            out[name][universe] = {
                "per_seed": per_seed,
                "noise_floor_seeds_0_99": floor,
                "cell_stability": stability,
                "k_sensitivity": v2b.k_sensitivity(stability),
                "seconds": round(time.time() - started, 1),
            }
            if verbose:
                clearing = [
                    k for k, v in stability.items() if v["clears_t_max_at_k3"]
                ]
                print(
                    f"  floors {name:>26} {universe:>18}: "
                    f"{out[name][universe]['seconds']:5.1f}s clearing {clearing}"
                )
    return out


def v2_reproduction_check(
    floors: dict[str, Any], v2_artifact: dict[str, Any]
) -> dict[str, Any]:
    """The survival-convention floors must equal v2's committed bytes.

    Both universes, all 100 seeds, all 14 cells: the floor VALUES and
    the stability blocks. This is the code-path tie that makes v3
    comparable to v2 -- and the survival end of the R6 band at once.
    """
    ref_universes = v2_artifact["internal_noise_floor"]["universes"]
    result: dict[str, Any] = {
        "purpose": (
            "v3 supersedes v2 only if it comes off the same code path and "
            "the same data; the survival convention rebuilt here at 100 "
            "seeds on both universes is compared to the committed v2 "
            "floors value by value before anything v3-specific is read"
        ),
        "v2_artifact": str(V2_PATH.relative_to(ROOT)),
        "v2_artifact_sha256": _sha_of_file(V2_PATH),
        "universes": {},
    }
    overall_max = 0.0
    for universe in UNIVERSES:
        got = floors[CONVENTION_SURVIVAL][universe]
        ref = ref_universes[universe]
        max_diff = 0.0
        for key, block in got["noise_floor_seeds_0_99"].items():
            for a, b in zip(
                block["values"],
                ref["noise_floor_seeds_0_99"][key]["values"],
                strict=True,
            ):
                max_diff = max(max_diff, abs(float(a) - float(b)))
        overall_max = max(overall_max, max_diff)
        result["universes"][universe] = {
            "cells_compared": len(got["noise_floor_seeds_0_99"]),
            "max_abs_diff_in_floor_values": float(max_diff),
            "floor_values_reproduce_exactly": bool(max_diff == 0.0),
            "stability_blocks_identical": bool(
                got["cell_stability"] == ref["cell_stability"]
            ),
        }
    result["max_abs_diff_in_floor_values"] = float(overall_max)
    result["reproduces_exactly"] = bool(
        overall_max == 0.0
        and all(
            u["stability_blocks_identical"]
            for u in result["universes"].values()
        )
    )
    return result


def convention_movement(
    frames: dict[str, pd.DataFrame], floors: dict[str, Any]
) -> dict[str, Any]:
    """Per cell x universe: hazard and tolerance under each convention."""
    out: dict[str, Any] = {}
    packet = {
        "estimate": "+3.9% on the numerator, ~0.038 log units, in every cell",
        "assumption": (
            "the 305 non-exact deaths ascertain at the exact deaths' "
            "0.483 rate (3775 / 7816) and enter every cell alike"
        ),
    }
    for universe, start in UNIVERSES.items():
        hazards = {
            name: _hazard_map(_window(frames[name], start))
            for name in CONVENTIONS
        }
        events = {
            name: float(_window(frames[name], start).death.sum())
            for name in CONVENTIONS
        }
        cells: dict[str, Any] = {}
        max_abs: dict[str, float] = {name: 0.0 for name in CONVENTIONS[1:]}
        max_dT: dict[str, float] = {name: 0.0 for name in CONVENTIONS[1:]}
        for key in CELL_ORDER:
            entry: dict[str, Any] = {
                "hazard": {},
                "ln_over_survival": {},
                "tolerance_k3": {},
                "delta_tolerance_k3": {},
            }
            base = hazards[CONVENTION_SURVIVAL].get(key, 0.0)
            base_t = floors[CONVENTION_SURVIVAL][universe]["cell_stability"][
                key
            ].get("tolerance_k3")
            for name in CONVENTIONS:
                m = hazards[name].get(key, 0.0)
                t = floors[name][universe]["cell_stability"][key].get(
                    "tolerance_k3"
                )
                entry["hazard"][name] = float(m)
                entry["tolerance_k3"][name] = t
                if name != CONVENTION_SURVIVAL:
                    lr = _log_ratio(m, base)
                    entry["ln_over_survival"][name] = lr
                    if lr is not None:
                        max_abs[name] = max(max_abs[name], abs(lr))
                    if t is not None and base_t is not None:
                        entry["delta_tolerance_k3"][name] = round(
                            t - base_t, 3
                        )
                        max_dT[name] = max(max_dT[name], abs(t - base_t))
            entry["clears_t_max_at_k3"] = {
                name: floors[name][universe]["cell_stability"][key][
                    "clears_t_max_at_k3"
                ]
                for name in CONVENTIONS
            }
            cells[key] = entry
        out[universe] = {
            "death_events_by_convention": events,
            "numerator_change_vs_survival_pct": {
                name: float(
                    100.0
                    * (events[name] - events[CONVENTION_SURVIVAL])
                    / events[CONVENTION_SURVIVAL]
                )
                for name in CONVENTIONS[1:]
            },
            "per_cell": cells,
            "max_abs_ln_over_survival": max_abs,
            "max_abs_delta_tolerance_k3": max_dT,
            "clearing_sets_k3": {
                name: sorted(
                    k
                    for k, v in floors[name][universe][
                        "cell_stability"
                    ].items()
                    if v["clears_t_max_at_k3"]
                )
                for name in CONVENTIONS
            },
        }
    declared = out["declared_1997_plus"]
    out["packet_estimate_replaced"] = {
        "packet": packet,
        "measured_declared_universe": {
            "numerator_change_pct": declared[
                "numerator_change_vs_survival_pct"
            ],
            "max_abs_ln_over_survival": declared["max_abs_ln_over_survival"],
            "max_abs_delta_tolerance_k3": declared[
                "max_abs_delta_tolerance_k3"
            ],
        },
        "measured_all_window": {
            "numerator_change_pct": out["all_v1_comparable"][
                "numerator_change_vs_survival_pct"
            ],
            "max_abs_ln_over_survival": out["all_v1_comparable"][
                "max_abs_ln_over_survival"
            ],
            "max_abs_delta_tolerance_k3": out["all_v1_comparable"][
                "max_abs_delta_tolerance_k3"
            ],
        },
        "why_the_estimate_was_high": (
            "the range codes carry information the estimate discarded: "
            "most record 'last seen at lo, found dead by hi' for persons "
            "whose last in-frame observation precedes lo, i.e. deaths "
            "after attrition that the censoring rule right-censors for "
            "exact deaths too; 119 of the 305 are not in the frame at "
            "all; and the packet's 0.483 is not a conditional "
            "ascertainment probability"
        ),
    }
    return out


def partition_movement_v2_to_v3(
    v2_artifact: dict[str, Any], stability_v3: dict[str, Any]
) -> dict[str, Any]:
    v2_stab = v2_artifact["internal_noise_floor"]["universes"][
        "declared_1997_plus"
    ]["cell_stability"]
    v2_clears = {k for k, v in v2_stab.items() if v["clears_t_max_at_k3"]}
    v3_clears = {k for k, v in stability_v3.items() if v["clears_t_max_at_k3"]}
    return {
        "basis": (
            "the k=3 tolerance round(mean + 3*sd, 3) against T_max = ln(1.5) "
            "on the declared universe: v2 (survival convention) vs v3 "
            "(pinned convention), both at 100 seeds on the identical "
            "person partitions"
        ),
        "v2_clearing": sorted(v2_clears),
        "v3_clearing": sorted(v3_clears),
        "demoted": sorted(v2_clears - v3_clears),
        "promoted": sorted(v3_clears - v2_clears),
        "unchanged": sorted(v2_clears & v3_clears),
        "tolerance_k3_v2_vs_v3": {
            key: {
                "v2": v2_stab[key].get("tolerance_k3"),
                "v3": stability_v3[key].get("tolerance_k3"),
                "delta": (
                    round(
                        stability_v3[key]["tolerance_k3"]
                        - v2_stab[key]["tolerance_k3"],
                        3,
                    )
                    if stability_v3[key].get("tolerance_k3") is not None
                    and v2_stab[key].get("tolerance_k3") is not None
                    else None
                ),
            }
            for key in CELL_ORDER
        },
    }


def seed_count_stability_v3(floor: dict[str, Any]) -> dict[str, Any]:
    """The 100-seed parametric bootstrap at the v3 pinned sigma."""
    per_cell: dict[str, Any] = {}
    for index, key in enumerate(CELL_ORDER):
        block = floor.get(key)
        if block is None:
            per_cell[key] = {}
            continue
        per_cell[key] = {
            "sigma_v3_100_seed": block["realized_sigma"],
            "at_100_seeds_sigma_v3": v2b._bootstrap_block(
                block["realized_sigma"], 100, v2b.BOOTSTRAP_B_100, index, 3
            ),
        }
    return {
        "question": (
            "at the pinned convention's own sigma, with what probability "
            "does a 100-seed floor place the cell's k=3 tolerance at or "
            "below ln(1.5)? Stream 3, the same rng stream v2 used for its "
            "100-seed question, at the v3 sigma"
        ),
        "t_max": T_MAX,
        "cell_order": list(CELL_ORDER),
        "per_cell": per_cell,
    }


def dominance_reading(
    full_panel_pinned: dict[str, float],
    full_panel_survival: dict[str, float],
    stability: dict[str, Any],
) -> dict[str, Any]:
    """Why the anchor is load-bearing, stated from the numbers.

    v2's reading said the clearing bands were "the two bands with the
    SMALLEST male/female log gaps". That was true of the survival
    convention and is measured again here under the pinned one, where
    the 75-84 gap rises above the 65-74 gap. The claim that survives
    measurement -- and the load-bearing one -- is that every clearing
    cell's full-panel sex gap sits inside its own k=3 tolerance, so a
    candidate that assigns both sexes one hazard reproduces every
    clearing cell. Whichever way the ranking falls is recorded, not
    asserted.
    """

    def _gaps(haz: dict[str, float]) -> dict[str, float]:
        return {
            band: float(
                abs(math.log(haz[f"{band}|male"] / haz[f"{band}|female"]))
            )
            for band in v1b.BAND_LABELS
            if haz.get(f"{band}|male", 0.0) > 0
            and haz.get(f"{band}|female", 0.0) > 0
        }

    gaps = _gaps(full_panel_pinned)
    gaps_survival = _gaps(full_panel_survival)
    clearing = sorted(
        k for k, v in stability.items() if v["clears_t_max_at_k3"]
    )
    band_order = list(v1b.BAND_LABELS)
    clearing_bands = sorted(
        {k.split("|")[0] for k in clearing}, key=band_order.index
    )
    ranking = sorted(gaps, key=lambda b: gaps[b])
    ranking_survival = sorted(gaps_survival, key=lambda b: gaps_survival[b])
    smallest = ranking[: len(clearing_bands)]
    smallest_survival = ranking_survival[: len(clearing_bands)]
    per_cell = {
        key: {
            "full_panel_abs_log_gap": gaps[key.split("|")[0]],
            "tolerance_k3": stability[key]["tolerance_k3"],
            "gap_within_tolerance": bool(
                gaps[key.split("|")[0]] <= stability[key]["tolerance_k3"]
            ),
        }
        for key in clearing
    }
    all_within = all(v["gap_within_tolerance"] for v in per_cell.values())
    holds_pinned = sorted(smallest) == sorted(clearing_bands)
    holds_survival = sorted(smallest_survival) == sorted(clearing_bands)
    gap_text = ", ".join(f"{b} {gaps[b]:.3f}" for b in clearing_bands)
    tol_text = ", ".join(
        f"{k} {stability[k]['tolerance_k3']}" for k in clearing
    )
    ranking_text = ", ".join(f"{b} {gaps[b]:.3f}" for b in ranking)
    ranking_survival_text = ", ".join(
        f"{b} {gaps_survival[b]:.3f}" for b in ranking_survival
    )
    verdict = (
        "still holds under the pinned convention"
        if holds_pinned
        else "does NOT hold under the pinned convention and is WITHDRAWN here"
    )
    return {
        "why_this_matters": (
            "the internal cells that clear the cap at 100 seeds are "
            f"{clearing}; each one's full-panel male/female log gap "
            f"({gap_text}) sits inside its own k=3 tolerance ({tol_text}), "
            "so a candidate that assigns both sexes one hazard reproduces "
            "every clearing cell"
            + (
                ""
                if all_within
                else " -- EXCEPT where gap_within_tolerance is false"
            )
            + ". v2's stronger reading, that the clearing bands are the "
            "bands with the SMALLEST gaps, "
            f"{verdict}: the full-panel gap ranking is {ranking_text} "
            f"(survival convention: {ranking_survival_text}). The dominance "
            "invariant is the only measured surface here that sees the sex "
            "differential at all. It is REPORTED, not gated: whether a "
            "margin this size is acceptable, and under which half "
            "convention, is the ceremony's ruling."
        ),
        "clearing_cells_gap_vs_tolerance": per_cell,
        "every_clearing_cell_gap_within_its_tolerance": bool(all_within),
        "band_gap_ranking": {
            "statistic": (
                "|ln(m_male / m_female)| per band on the full declared "
                "panel, ascending"
            ),
            "clearing_bands": clearing_bands,
            "pinned_narrow_midpoint": {"gaps": gaps, "ascending": ranking},
            "survival_v1_v2": {
                "gaps": gaps_survival,
                "ascending": ranking_survival,
            },
            "smallest_gap_bands_are_the_clearing_bands": {
                "pinned_narrow_midpoint": bool(holds_pinned),
                "survival_v1_v2": bool(holds_survival),
            },
        },
    }


# --------------------------------------------------------------------------
# Prose blocks
# --------------------------------------------------------------------------
def proposed_thresholds_note(
    stability: dict[str, Any],
    movement: dict[str, Any],
    conv: dict[str, Any],
    weights: dict[str, Any],
    dominance: dict[str, Any],
) -> str:
    clearing = sorted(
        k for k, v in stability.items() if v["clears_t_max_at_k3"]
    )
    not_clearing = sorted(
        k for k, v in stability.items() if not v["clears_t_max_at_k3"]
    )
    declared = conv["declared_1997_plus"]
    headline = dominance["headline"]
    return (
        "PROPOSED VALIDATION BASIS FOR THE DIFFERENTIAL-MORTALITY "
        "COMPONENT -- NOT RATIFIED.\n\n"
        "This artifact supersedes runs/mortality_floors_v2.json as the "
        "FLOOR BASIS and ratifies nothing. It reads no gate, changes no "
        "gate, edits no threshold and touches gates.yaml not at all. "
        "Ratification still requires the full ceremony (issue #74 "
        "comment 4907496891): floors -> thresholds with machine-bound "
        "derivations -> an adversarial referee round -> verification -> "
        "maintainer ratification by merge. No candidate has been scored "
        "against anything here.\n\n"
        "STATISTIC. Per age band x sex, the weighted PSID central death "
        "rate m(band, sex) = sum(w * death) / sum(w * exposure) over the "
        "person-interval exposure slices, on the DECLARED weight universe "
        "under the PINNED death-ascertainment convention and the "
        "DECLARED censoring convention (governance). A candidate-vs-PSID "
        "discrepancy would be scored as |ln(m_candidate / m_PSID)| on a "
        "frame built with the same three conventions.\n\n"
        "WEIGHT UNIVERSE (R1). CORE/IMM INDIVIDUAL CROSS-SECTION WT, "
        "interval start waves 1997-2023. The per-wave resolution table "
        "is committed in weight_universe.resolution_table with each "
        "series' codebook target population and SPSS storage format; "
        "the pre-1997 series are family-scale decimals and carry "
        f"{100 * weights['pre_1997']['share_of_weighted_exposure']:.4f}% "
        "of the weighted exposure. v1's caveat that older decades bias "
        "PSID upward is WITHDRAWN with three measurements "
        "(weight_universe.withdrawal_of_v1_caveat).\n\n"
        "DEATH ASCERTAINMENT (R6). Narrow range codes (span <= 2 years, "
        "200 of 293) are assigned floor((lo + hi) / 2) and scored by the "
        "exact-year machinery; the 93 wide codes and 12 NA-year deaths "
        "are a published sensitivity band. Measured on the declared "
        "universe, the pinned convention adds "
        f"{declared['numerator_change_vs_survival_pct'][CONVENTION_PINNED]:.2f}% "
        "to the numerator and moves no cell's k=3 tolerance by more "
        f"than {declared['max_abs_delta_tolerance_k3'][CONVENTION_PINNED]:.3f}; "
        "the packet's +3.9% / 0.038-log estimate is replaced by that "
        "measurement. The convention binds both sides of every score.\n\n"
        "CENSORING (R7). Exposure ends at the last observed wave and a "
        "death more than one grid interval later is never counted. That "
        "is valid under non-informative nonresponse, and the PSID/NCHS "
        "ratios plus the attrition-by-age table in governance.censoring "
        "are the direct measurement that the assumption fails, most "
        "severely at 85+.\n\n"
        "SEED COUNT. 100 person-disjoint half-split seeds (0-99) on the "
        "pinned full-frame split. Against v2's clearing set the pinned "
        f"convention DEMOTES {movement['demoted']} and PROMOTES "
        f"{movement['promoted']}. Cells whose k=3 tolerance clears "
        f"ln(1.5): {clearing}. Cells above the cap at k=3: "
        f"{not_clearing}. k itself is NOT fixed here; tolerances at "
        "k=2, 3 and 4 are published per cell.\n\n"
        "EXTERNAL ANCHOR. The NCHS 2023 US period life tables, "
        "sha-pinned, aggregated to these bands. Every ratio is below 1 "
        "in every window; the anchor must NOT gate a level match to "
        "NCHS (gates.yaml:5737-5740).\n\n"
        "SEX DIFFERENTIAL. The dominance invariant over "
        f"{headline['band_set']} is measured at "
        f"{headline['margin_sigma_units_side_a']} half-split sd units "
        f"(side A; {headline['margin_sigma_units_both_sides']} over all "
        f"200 halves) against MARGIN_K = {MARGIN_K}, on the pinned "
        "convention. REPORTED, NOT GATED.\n\n"
        "SCOPE OF THE ln(1.5) CAP. gates.yaml:5396-5405 is gate_m6's "
        "TEMPORAL-HOLDOUT DRIFT surface; this is the person-disjoint "
        "REPRODUCTION surface. Nothing here weakens "
        "gate_m6.not_certified[0].\n\n"
        "BASELINE CONVENTION. Any scored reform must state whether it "
        "runs against the scheduled or payable baseline (issue #74 "
        "protocol note 1). This artifact fixes none of that."
    )


def open_questions_for_the_ceremony() -> list[dict[str, str]]:
    return [
        {
            "question": "weighted vs unweighted event-count eligibility",
            "detail": (
                "v1's rule counts UNWEIGHTED deaths on the weaker half "
                "while the gated statistic is WEIGHTED. The Kish effective "
                "weighted count is published per cell "
                "(min_effective_deaths_kish); this artifact applies "
                "NEITHER as a gate rule."
            ),
        },
        {
            "question": "85+ eligibility for a reproduction gate",
            "detail": (
                "gate_m6 partitions death.85+|{male,female} report-only "
                "with the machine reason attrition_confounded_truth. Both "
                "85+ cells clear the cap on this surface, and the R4 "
                "attrition evidence now published in governance.censoring "
                "shows attrition and death least separable at 85+. "
                "Whether that disqualifies them from a REPRODUCTION gate "
                "is a referee ruling; this artifact reports and rules "
                "nothing."
            ),
        },
        {
            "question": "k, and the MARGIN_K ruling for the anchor",
            "detail": (
                "tolerances at k=2, 3 and 4 are published per cell and no "
                "k is adopted. The dominance margin is published under "
                "both half conventions."
            ),
        },
        {
            "question": "the within-rule tie-break for span-2 range codes",
            "detail": (
                "the pinned rule takes the midpoint year; assigning at lo "
                "or at hi instead is measured in "
                "death_ascertainment.within_rule_sensitivity. The referee "
                "round may prefer a different tie-break; the frame is "
                "rebuilt by changing one line."
            ),
        },
        {
            "question": "post-death observed waves",
            "detail": (
                "a handful of exact decedents carry in-family observations "
                "after their recorded death year; the inherited rule "
                "credits them as exposure and the effect is measured "
                "(data.post_death_observations). Adjudicating the record "
                "is not this artifact's act."
            ),
        },
    ]


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
def run(verbose: bool = True) -> dict[str, Any]:
    started = time.time()
    nchs = json.loads(NCHS_PATH.read_text())
    nchs_rates = v1b.nchs_band_rates(nchs)
    v1_artifact = json.loads(V1_PATH.read_text())
    v2_artifact = json.loads(V2_PATH.read_text())

    demo = panels.demographic_panel()
    dr = deaths.read_death_records()
    frames, ascertainment = build_convention_frames(demo, dr)
    survival = frames[CONVENTION_SURVIVAL]
    pinned = frames[CONVENTION_PINNED]
    if verbose:
        for name, frame in frames.items():
            print(
                f"frame {name:>26}: {len(frame)} slices, "
                f"{frame.person_id.nunique()} persons, "
                f"{frame.death.sum():.3f} death events"
            )

    # --- floors under every convention, survival first as the tie ------
    floors = build_floors(frames, verbose)
    v2_check = v2_reproduction_check(floors, v2_artifact)
    if verbose:
        print(
            f"v2 reproduction: max|diff| {v2_check['max_abs_diff_in_floor_values']!r}"
        )
    if not v2_check["reproduces_exactly"]:
        raise RuntimeError(
            "the committed v2 100-seed floors did not reproduce on the "
            "survival convention; v3 is not comparable to v2 and the build "
            "stops"
        )
    # The v3 measure_seed must agree with v2's on an integer-death frame.
    probe_v3 = measure_seed(
        0, survival, start_year_min=DECLARED_UNIVERSE_START
    )
    probe_v2 = v2b.measure_seed(
        0, survival, start_year_min=DECLARED_UNIVERSE_START
    )
    if probe_v3["cells"] != probe_v2["cells"]:
        raise RuntimeError(
            "v3 measure_seed diverges from v2 on the survival frame"
        )

    # --- R1 ------------------------------------------------------------
    table = weight_resolution_table()
    series_by_wave = {r["wave"]: r["series"] for r in table}
    if series_by_wave != v2b.weight_series_by_wave():
        raise RuntimeError(
            "the resolution table disagrees with v2's series map"
        )
    weights = v2b.weight_universe_report(survival, series_by_wave)
    equivalence = v2b.universe_equivalence(survival)
    series_summary = weight_series_summary(table, survival)
    anchor_all_survival = v1b.external_anchor(
        survival, nchs_rates, start_year_min=None
    )
    withdrawal = withdrawal_of_v1_caveat(
        survival,
        v1_artifact,
        v2_artifact,
        weights,
        series_summary,
        equivalence,
        anchor_all_survival,
    )
    strata = sample_stratum_shares(survival)
    cell_shares = per_cell_series_shares(survival, series_by_wave)

    # --- R6 ------------------------------------------------------------
    conv = convention_movement(frames, floors)
    sensitivity = within_rule_sensitivity(demo, dr, pinned)
    post_death = post_death_observation_note(survival, dr)

    # --- R7 ------------------------------------------------------------
    grid, next_wave = _grid(demo)
    obs = _observed_frame(demo, dr)
    dr_pinned = assign_narrow_death_years(dr)
    pi = person_interval_table(obs, dr_pinned, dr, next_wave)
    attrition = attrition_evidence(pi)
    anchors_pinned = {
        "all": v1b.external_anchor(pinned, nchs_rates, start_year_min=None),
        "recent": v1b.external_anchor(
            pinned, nchs_rates, start_year_min=v1b.RECENT_START_YEAR
        ),
        "declared_1997_plus": v1b.external_anchor(
            pinned, nchs_rates, start_year_min=DECLARED_UNIVERSE_START
        ),
    }
    anchors_survival = {
        "all": anchor_all_survival,
        "declared_1997_plus": v1b.external_anchor(
            survival, nchs_rates, start_year_min=DECLARED_UNIVERSE_START
        ),
    }
    censoring = censoring_governance(
        censoring_rule_quote(),
        {
            "all_pinned": anchors_pinned["all"],
            "declared_1997_plus_pinned": anchors_pinned["declared_1997_plus"],
            "all_survival_v1_v2": anchors_survival["all"],
            "declared_1997_plus_survival_v1_v2": anchors_survival[
                "declared_1997_plus"
            ],
        },
        attrition,
    )

    # --- headline floor: pinned convention, declared universe -----------
    head = floors[CONVENTION_PINNED]["declared_1997_plus"]
    movement = partition_movement_v2_to_v3(v2_artifact, head["cell_stability"])
    bootstrap = seed_count_stability_v3(head["noise_floor_seeds_0_99"])
    declared_pinned = _window(pinned, DECLARED_UNIVERSE_START)
    full_panel_haz = _hazard_map(declared_pinned)
    halves_a = v2b._half_hazard_vectors(head["per_seed"], sides=("a",))
    halves_both = v2b._half_hazard_vectors(head["per_seed"], sides=("a", "b"))
    dominance = v2b.sex_dominance_anchor(full_panel_haz, halves_a, halves_both)
    gradient = v2b.age_gradient_companion(
        full_panel_haz, halves_a, halves_both
    )
    dominance.update(
        dominance_reading(
            full_panel_haz,
            _hazard_map(_window(survival, DECLARED_UNIVERSE_START)),
            head["cell_stability"],
        )
    )
    if verbose:
        for key in CELL_ORDER:
            st = head["cell_stability"][key]
            print(
                f"  {key:>14}: T(k=3)={st.get('tolerance_k3')} "
                f"sigma={st.get('realized_sigma', 0):.5f} "
                f"minD={st['min_deaths_either_half']} kish={st['min_effective_deaths_kish']} "
                f"{'CLEARS' if st['clears_t_max_at_k3'] else st['report_reason']}"
            )
        h = dominance["headline"]
        print(
            f"dominance {h['band_set']} margin {h['margin_sigma_units_side_a']} / "
            f"{h['margin_sigma_units_both_sides']}"
        )

    ind_dir = _psid_ind_dir()
    artifact: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "run": "mortality_floors_v3",
        "reported_anchor_not_gated": True,
        "component": "differential mortality (issue #74 Phase B; task B1)",
        "purpose": (
            "The mortality floor basis with the pre-registration packet's "
            "three data-side blockers answered from bytes: the weight "
            "universe declared from the release's own resolution table "
            "(R1), a pinned death-ascertainment convention with its "
            "sensitivity band measured cell by cell (R6), and the "
            "censoring convention declared with its assumption and the "
            "evidence against it (R7). Rebuilt at 100 seeds on both "
            "universes under every convention. This reads no gate and "
            "changes no gate on its own; gates.yaml is untouched. The "
            "pre-registered gate ceremony (issue #74 comment 4907496891) "
            "comes after. See proposed_thresholds_note (NOT RATIFIED)."
        ),
        "supersedes": {
            "artifact": str(V2_PATH.relative_to(ROOT)),
            "sha256": _sha_of_file(V2_PATH),
            "as": "the floor / derivation basis",
            "v2_retained_as": (
                "the 100-seed rebuild under the inherited conventions; "
                "NOT deleted, NOT edited, its own reproduction test still "
                "pins it. v1 likewise (runs/mortality_floors_v1.json)."
            ),
            "v1_artifact_sha256": _sha_of_file(V1_PATH),
        },
        "what_changed_from_v2": [
            "the weight-variable resolution table is committed per wave "
            "with codebook target populations and SPSS storage formats "
            "(R1.1), per-cell exposure and death shares by series (R1.2), "
            "and the sample-stratum composition by era",
            "v1's biennial_caveats[1] is withdrawn with three "
            "measurements, not restated (R1.4)",
            "a death-ascertainment convention is PINNED: narrow range "
            "codes at floor((lo+hi)/2); the residue is a published "
            "sensitivity band with two upper ends (R6.1)",
            "every cell's hazard and tolerance is measured under four "
            "conventions on both universes at 100 seeds, replacing the "
            "packet's +3.9% / 0.038-log estimate (R6.2)",
            "governance blocks state that the ascertainment and "
            "censoring conventions bind both sides of every score (R6.3, "
            "R7)",
            "governance.censoring names the rule, its assumption, the "
            "PSID/NCHS ratios and the attrition-hazard-by-age table (R7, "
            "shared with R4)",
        ],
        "does_not_do": [
            "edit gates.yaml or any threshold",
            "score a candidate or run a gate",
            "adopt a k, a gate partition or an eligibility rule",
            "rule on 85+ eligibility",
            "delete, edit or supersede any other runs/ artifact",
        ],
        "t_max_scope": dict(
            v2_artifact["t_max_scope"],
            which_surface_this_artifact_is_about=(
                "the person-disjoint half-split REPRODUCTION surface, "
                f"{int(round(float(pinned.death.sum())))} death events on "
                "the full window and "
                f"{int(round(float(declared_pinned.death.sum())))} on the "
                "declared 1997+ universe under the pinned convention -- a "
                "different question (reproduction, not drift) on a much "
                "larger event base, the same split gate_m4 and gate_m6 "
                "already draw for disability."
            ),
            m6_reference=dict(
                v2_artifact["t_max_scope"]["m6_reference"],
                sha256=_sha_of_file(M6_PATH),
            ),
        ),
        "gates_yaml_citations": v2b.gates_yaml_citations(),
        "data": {
            "psid_population": v1_artifact["data"]["psid_population"],
            "psid_wave_calendar": v1_artifact["data"]["psid_wave_calendar"],
            "psid_release": {
                "individual_file": "ind2023er / IND2023ER.txt (1968-2023 Public Release Individual File, Release 2, December 2025)",
                "data_sha256": _sha_of_file(ind_dir / "IND2023ER.txt"),
                "sps_sha256": _sha_of_file(ind_dir / "IND2023ER.sps"),
                "codebook_sha256": _sha_of_file(
                    ind_dir / "IND2023ER_codebook.pdf"
                ),
            },
            "n_persons_with_exposure": int(survival.person_id.nunique()),
            "n_slices": int(len(survival)),
            "death_record_counts": {
                **{
                    k: int(v)
                    for k, v in ascertainment["classification"][
                        "status_counts"
                    ].items()
                },
                "range_narrow_span_le_2": ascertainment["classification"][
                    "narrow"
                ]["n"],
                "range_wide_span_ge_3": ascertainment["classification"][
                    "wide"
                ]["n"],
                "note": (
                    "counts over the 85,536 individual records; how each "
                    "class is scored is fixed by "
                    "death_ascertainment.convention and its band"
                ),
            },
            "post_death_observations": post_death,
            "person_identity_check": v2_artifact["data"][
                "person_identity_check"
            ],
        },
        "exposure_construction": {
            "unit": v1_artifact["exposure_construction"]["unit"],
            "rule": v1_artifact["exposure_construction"]["rule"],
            "weight": v1_artifact["exposure_construction"]["weight"],
            "biennial_caveats": [
                "deaths counted only in the one grid interval after an "
                "observed wave; later deaths of attriters are "
                "right-censored and NOT counted. DECLARED in "
                "governance.censoring with its assumption and the evidence "
                "against it",
                "narrow range-coded deaths (span <= 2) are assigned "
                "floor((lo+hi)/2) and scored like exact deaths; wide codes "
                "and NA-year deaths are scored as survival in the headline "
                "and as a fractional death at the measured ascertainment "
                "rate in the band's upper ends. PINNED in "
                "governance.death_ascertainment",
                "start-wave weight shared by a biennial interval's two "
                "slices; band assigned per slice-age",
                "the declared universe is a WEIGHT universe, not a period "
                "claim (weight_universe.declaration)",
            ],
            "withdrawn_v1_caveat": {
                "text": v1_artifact["exposure_construction"][
                    "biennial_caveats"
                ][1],
                "see": "weight_universe.withdrawal_of_v1_caveat",
            },
        },
        "weight_universe": {
            "resolution_rule": (
                "populace_dynamics.data.panels.DEMOGRAPHIC_CONCEPTS['weight'] "
                "ordered fallback replayed against the real ind2023er label "
                "space via psid.parse_sps_labels(psid.product_sps_path("
                "'ind2023er')) -> panels.wave_variables per pattern; a "
                "slice's series is the one resolved at its START wave"
            ),
            "fallback_patterns": list(panels.DEMOGRAPHIC_CONCEPTS["weight"]),
            "resolution_table": table,
            "series": series_summary,
            "n_series_across_window": len(series_summary),
            "measurement": weights,
            "universe_equivalence": equivalence,
            "sample_strata": strata,
            "per_cell_shares": cell_shares,
            "declaration": {
                "declared_weight_universe": (
                    "CORE/IMM INDIVIDUAL CROSS-SECTION WT, interval start "
                    "waves 1997-2023"
                ),
                "declared_universe_start_wave": DECLARED_UNIVERSE_START,
                "why": [
                    "it is the only series whose codebook target population "
                    "is a cross-sectional US-resident population "
                    "('Core-Immigrant Individual Cross-sectional Weight'); "
                    "the 1968-1996 series are core-sample-only weights and "
                    "the 1993-1996 one is explicitly LONGITUDINAL",
                    "it is the only series stored population-scaled (F6.0 / "
                    "F5.0, values to 118,766); the others are family-scale "
                    "decimals (F4.1 / F7.3, values to 131.9), so the "
                    "resolved 'weight' column changes meaning at 1997",
                    "measured, the 1997+ slices carry "
                    f"{100 * weights['from_1997']['share_of_weighted_exposure']:.4f}% "
                    "of the weighted exposure; the pooled all-window rate is "
                    "the 1997+ rate to "
                    f"{equivalence['max_abs_log_ratio']:.6f} log units",
                    "the all-window universe is retained as a report-only "
                    "sensitivity under every convention so the movement is "
                    "visible, never pooled into the declared statistic",
                ],
                "within_universe_composition_change": (
                    "the 2017/2019 Immigrant refresher (ER30001=4001-4851) "
                    "enters the cross-section weight at the 2017 wave; its "
                    "measured share of 2017+ weighted exposure and deaths is "
                    "in sample_strata.by_era['2017_plus']. The target "
                    "population -- the US resident population each wave -- "
                    "is unchanged; the sample composition is not"
                ),
            },
            "withdrawal_of_v1_caveat": withdrawal,
        },
        "death_ascertainment": {
            "convention": {
                "name": CONVENTION_PINNED,
                "rule": (
                    "a range code lo-hi with span = hi - lo <= 2 years is "
                    "assigned the death year floor((lo + hi) / 2) -- lo for "
                    "a span-1 code, lo + 1 for a span-2 code -- and is then "
                    "scored by the exact-year machinery unchanged: counted "
                    "iff the person was observed at the start of the grid "
                    "interval containing that year; the death-year slice "
                    "carries exposure 0.5 and one death and later slices in "
                    "the interval carry nothing. Wide codes (span >= 3) and "
                    "NA-year deaths carry full exposure and zero deaths in "
                    "the headline floor (the survival treatment) and are "
                    "published as the sensitivity band below"
                ),
                "why_the_midpoint": (
                    "166 of the 200 narrow codes are exactly one grid "
                    "interval ('last seen at lo, found dead by hi'), so the "
                    "assignment lands in the interval a death would be "
                    "ascertained in; within a biennial interval the exact "
                    "ascertained deaths fall in the second year "
                    f"{100 * ascertainment['ascertainment_rates']['within_two_year_interval_split']['p_second_year']:.1f}% "
                    "of the time, so the midpoint of a span-2 code is its "
                    "modal year"
                ),
                "narrow_max_span": NARROW_MAX_SPAN,
                "implementation": "scripts/build_mortality_floors_v3.py assign_narrow_death_years",
            },
            "classification": ascertainment["classification"],
            "grid": ascertainment["grid"],
            "pinned_rule_effect": ascertainment["pinned_rule_effect"],
            "ascertainment_rates": ascertainment["ascertainment_rates"],
            "sensitivity_band": {
                "residue": "93 wide range codes (span >= 3) + 12 NA-year deaths",
                "lower_end": {
                    "convention": CONVENTION_SURVIVAL,
                    "rule": (
                        "every non-exact death scored as survival: full "
                        "exposure and zero deaths in every interval (v1 and "
                        "v2's treatment; in v3 the headline applies it to the "
                        "residue only)"
                    ),
                },
                "upper_end_informed": {
                    "convention": CONVENTION_UPPER_INFORMED,
                    "rule": (
                        "each residue decedent in the frame is scored as "
                        "dying in the grid interval after their last "
                        "observed wave with probability r = the exact "
                        "deaths' in-frame ascertainment rate, where the "
                        "record permits it: a wide code only if its range "
                        "overlaps that interval, with only the years inside "
                        "the range feasible; an NA-year death with every "
                        "year of the interval feasible. Expected exposure "
                        "and expected deaths replace the person's slices "
                        "(death slice exposure 0.5), the death split across "
                        "the two slices of a biennial interval by the "
                        "measured second-year share"
                    ),
                    "targets": ascertainment["upper_band_targets"][
                        CONVENTION_UPPER_INFORMED
                    ],
                },
                "upper_end_packet_literal": {
                    "convention": CONVENTION_UPPER_LITERAL,
                    "rule": (
                        "the packet's assumption taken literally: every "
                        "in-frame non-exact decedent not already assigned "
                        "by the pinned rule is scored as dying in the "
                        "interval after their last observed wave with "
                        "probability r, IGNORING what their range says. "
                        "Contradicted by the ranges for most of them "
                        "(classification.*.in_frame_last_wave_before_lo); "
                        "published as the extreme the estimate implied"
                    ),
                    "targets": ascertainment["upper_band_targets"][
                        CONVENTION_UPPER_LITERAL
                    ],
                },
                "r_used": ascertainment["ascertainment_rates"][
                    "rule_rate_used_by_the_band"
                ],
                "p_second_year_used": ascertainment["ascertainment_rates"][
                    "within_two_year_interval_split"
                ]["p_second_year"],
                "expected_death_events_by_convention": ascertainment[
                    "expected_death_events_by_convention"
                ],
                "expected_death_events_by_convention_declared_universe": ascertainment[
                    "expected_death_events_by_convention_declared_universe"
                ],
            },
            "measured_movement": conv,
            "within_rule_sensitivity": sensitivity,
        },
        "governance": {
            "weight_universe": {
                "declared": "weight_universe.declaration",
                "binds": (
                    "the declared universe binds both sides of every score: "
                    "truth and candidate are scored on start waves 1997+ "
                    "under the cross-section weight, and the all-window "
                    "floor is report-only"
                ),
            },
            "death_ascertainment": {
                "convention": CONVENTION_PINNED,
                "declared": "death_ascertainment.convention",
                "sensitivity_band": "death_ascertainment.sensitivity_band",
                "binds_both_sides": (
                    "the convention binds both sides of every score. The "
                    "PSID truth half and any candidate are scored on frames "
                    "built with the same assignment rule for narrow range "
                    "codes and the same treatment of the residue; a "
                    "candidate that ascertains deaths differently is scored "
                    "on this frame's convention, not its own, and the band "
                    "is the disclosed uncertainty of the truth, never a "
                    "second scoring rule"
                ),
            },
            "censoring": censoring,
        },
        "estimand": {
            "statistic": v2_artifact["estimand"]["statistic"],
            "declared_weight_universe": "CORE/IMM INDIVIDUAL CROSS-SECTION WT, interval start waves 1997-2023",
            "declared_universe_start_wave": DECLARED_UNIVERSE_START,
            "death_ascertainment_convention": CONVENTION_PINNED,
            "censoring_convention": "governance.censoring.rule",
            "see": "weight_universe, death_ascertainment, governance",
        },
        "age_bands": list(v1b.BAND_LABELS),
        "sexes": list(v1b.SEXES),
        "cell_order": list(CELL_ORDER),
        "external_anchor": {
            "nchs_reference_file": str(NCHS_PATH.relative_to(ROOT)),
            "nchs_vintage_year": nchs["vintage_year"],
            "nchs_citation": nchs["report"]["nvsr_citation"],
            "nchs_reference_sha256": _sha_of_file(NCHS_PATH),
            "nchs_source_file_sha256": {
                pop: meta["sha256"]
                for pop, meta in nchs["fetch"]["source_files"].items()
            },
            "band_central_rate_formula": v1_artifact["external_anchor"][
                "band_central_rate_formula"
            ],
            "undercount_note": v1_artifact["external_anchor"][
                "undercount_note"
            ],
            "gating_ruling_inherited": v2_artifact["external_anchor"][
                "gating_ruling_inherited"
            ],
            "concept_deltas_named": [
                "ascertainment (censoring): a death is counted only in the "
                "one grid interval after an observed wave -- declared in "
                "governance.censoring",
                "death dating: narrow range codes assigned at the midpoint, "
                "wide codes and NA-year deaths scored as survival -- pinned "
                "in governance.death_ascertainment",
                "weight universe: the declared window is 1997+ "
                "(weight_universe.declaration)",
                "period: interval deaths against a 2023 period table",
            ],
            "convention": CONVENTION_PINNED,
            "windows": anchors_pinned,
            "windows_survival_v1_v2_convention": anchors_survival,
        },
        "internal_noise_floor": {
            "method": v2_artifact["internal_noise_floor"]["method"],
            "split_unit": "person",
            "split_fraction": 0.5,
            "split_frame_pin": (
                v2_artifact["internal_noise_floor"]["split_frame_pin"]
                + " Every convention's frame carries the identical person "
                "set, so seed s draws the identical partition under every "
                "convention as well."
            ),
            "floor_seeds": list(FLOOR_SEEDS),
            "seed_count": len(FLOOR_SEEDS),
            "seed_count_precedent": v2_artifact["internal_noise_floor"][
                "seed_count_precedent"
            ],
            "t_max": T_MAX,
            "t_max_source": "ln(1.5)",
            "tolerance_convention": v2_artifact["internal_noise_floor"][
                "tolerance_convention"
            ],
            "headline": {
                "convention": CONVENTION_PINNED,
                "universe": "declared_1997_plus",
                "role": "the declared estimand; the derivation basis",
            },
            "conventions": {
                name: {
                    "role": {
                        CONVENTION_SURVIVAL: (
                            "v1/v2's convention; the band's lower end; equal "
                            "to the committed v2 floors (v2_reproduction_check)"
                        ),
                        CONVENTION_PINNED: "the pinned convention; the headline",
                        CONVENTION_UPPER_INFORMED: "the band's informed upper end",
                        CONVENTION_UPPER_LITERAL: "the band's packet-literal upper end",
                    }[name],
                    "per_seed_shape": {
                        CONVENTION_SURVIVAL: (
                            "v2 full shape, committed in v2 (identical)"
                        ),
                        CONVENTION_PINNED: (
                            "declared_1997_plus: v2 full shape (cells with "
                            "pct_diff_abs; per-half hazard vectors); "
                            "all_v1_comparable: compact (cells only, with "
                            "deaths_expected_a/b)"
                        ),
                        CONVENTION_UPPER_INFORMED: "not committed",
                        CONVENTION_UPPER_LITERAL: "not committed",
                    }[name],
                    "universes": {
                        universe: {
                            "start_year_min": UNIVERSES[universe],
                            "noise_floor_seeds_0_99": block[
                                "noise_floor_seeds_0_99"
                            ],
                            "cell_stability": block["cell_stability"],
                            "k_sensitivity": block["k_sensitivity"],
                            "per_seed": (
                                block["per_seed"]
                                if name == CONVENTION_PINNED
                                else None
                            ),
                            "per_seed_reference": (
                                "runs/mortality_floors_v2.json internal_noise_floor."
                                f"universes.{universe}.per_seed (identical; see "
                                "v2_reproduction_check)"
                                if name == CONVENTION_SURVIVAL
                                else (
                                    None
                                    if name == CONVENTION_PINNED
                                    else "not committed (size); the per-seed "
                                    "|ln| values are noise_floor_seeds_0_99[cell]"
                                    ".values and the per-half death counts are "
                                    "summarised in cell_stability; rebuild with "
                                    "scripts/build_mortality_floors_v3.py (~7 s)"
                                )
                            ),
                        }
                        for universe, block in floors[name].items()
                    },
                }
                for name in CONVENTIONS
            },
            "universe_partition_agreement_pinned": {
                "declared_clearing_t_max_at_k3": conv["declared_1997_plus"][
                    "clearing_sets_k3"
                ][CONVENTION_PINNED],
                "all_clearing_t_max_at_k3": conv["all_v1_comparable"][
                    "clearing_sets_k3"
                ][CONVENTION_PINNED],
                "agree": bool(
                    conv["declared_1997_plus"]["clearing_sets_k3"][
                        CONVENTION_PINNED
                    ]
                    == conv["all_v1_comparable"]["clearing_sets_k3"][
                        CONVENTION_PINNED
                    ]
                ),
            },
        },
        "v2_reproduction_check": v2_check,
        "seed_count_stability": bootstrap,
        "partition_movement": {"v2_survival_to_v3_pinned_declared": movement},
        "anchor_invariants": {
            "reported_not_gated": True,
            "universe": "declared_1997_plus",
            "convention": CONVENTION_PINNED,
            "half_conventions": v2_artifact["anchor_invariants"][
                "half_conventions"
            ],
            "sex_dominance": dominance,
            "age_gradient_companion": gradient,
        },
        "open_questions_for_the_ceremony": open_questions_for_the_ceremony(),
        "proposed_thresholds_note": proposed_thresholds_note(
            head["cell_stability"], movement, conv, weights, dominance
        ),
        "revision_pins": {
            "populace_dynamics_sha": _git_sha(ROOT),
            "nchs_reference_sha256": _sha_of_file(NCHS_PATH),
            "v1_artifact_sha256": _sha_of_file(V1_PATH),
            "v2_artifact_sha256": _sha_of_file(V2_PATH),
            "gates_yaml_sha256": _sha_of_file(GATES_PATH),
            "builder_v1_sha256": _sha_of_file(BUILDER_V1_PATH),
            "builder_v2_sha256": _sha_of_file(BUILDER_V2_PATH),
            "psid_ind2023er_txt_sha256": _sha_of_file(
                ind_dir / "IND2023ER.txt"
            ),
            "psid_ind2023er_sps_sha256": _sha_of_file(
                ind_dir / "IND2023ER.sps"
            ),
            "psid_ind2023er_codebook_sha256": _sha_of_file(
                ind_dir / "IND2023ER_codebook.pdf"
            ),
            "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        },
        "elapsed_seconds": round(time.time() - started, 1),
    }
    return artifact


def main() -> None:
    artifact = run(verbose=True)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"wrote {ARTIFACT_PATH} ({ARTIFACT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
