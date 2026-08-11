"""Observed firm frame — real sponsor records reweighted to SUSB (#192).

The employer-firm design originally assumed a **generated** firm
population, on the premise that no public firm microdata existed. It
does (``data/form5500.py``, ``data/osha_ita.py``), and it covers the
calibration grid densely enough to reweight instead of generate.
Measured against the committed SUSB 2022 extract, Form 5500 sponsors
alone populate **all 97** sector x canonical-band cells with at least
ten records each and 0.000% of SUSB employment in an under-covered
cell. So this module builds the firm population by **post-stratifying
observed sponsor records**, and no synthetic firm row is created.

**One source defines the frame; the other validates it.** Form 5500
sponsors and OSHA ITA establishments are *different units* — the two
sources agree on the canonical band for only 66.3% of the 43,001 EINs
they share, with disagreement running in both directions. Unioning
them would silently mix a plan-sponsor unit with an establishment
unit. The frame is therefore Form 5500 only, and OSHA ITA is retained
as an independent measurement reference (see
:func:`band_agreement_reference`). Mixing is a design error, not a
coverage improvement.

**What post-stratification does and does not fix.** Cell weights are
``SUSB firms in cell / observed records in cell``, so the weighted
firm count matches SUSB **exactly, by construction**, in every cell.
It does not fix *within-cell* selection: a plan-sponsoring firm may
differ systematically from a non-sponsor of the same size and sector.
That is the same limitation RAND COMPARE carries when it reweights
Kaiser/HRET records, and it is documented rather than solved.

**Employment is deliberately not forced to match — and measuring it
falsifies the naive design.** ``Active participants`` count
plan-covered workers, a lower bound on employment *per firm*, so the
weighted participant total was expected to fall short of SUSB
employment. Measured on the 2023 files it does the opposite:

======================  ==========  ==========  ======
band                    sponsor     SUSB        ratio
                        mean size   mean size
======================  ==========  ==========  ======
``LT10``                      4.62        2.59    1.78
``B10_49``                   21.99       19.76    1.11
``B50_99``                   69.13       64.60    1.07
``B100_499``                213.33      161.15    1.32
``B500_PLUS``             4,364.97    1,675.47    2.61
======================  ==========  ==========  ======

Weighted participants total **279,300,780 against SUSB's 135,748,407
— 2.06x**. Firm counts match exactly and employment is off by more
than a factor of two.

The cause is **within-cell selection**, the limitation named above,
and it is large rather than marginal. A firm must be big enough to
sponsor an ERISA plan at all, so the sponsors sitting in a given band
are systematically the *larger* firms in that band, while SUSB's band
is dominated by the many non-sponsoring firms below them. Post-
stratifying on firm count then multiplies those over-large records by
the cell weight. ``B500_PLUS`` is worst because a second effect
compounds it: the sponsor EIN is frequently a parent enterprise
aggregating several operating subsidiaries (``data/form5500.py``).

So :func:`post_stratify` as written produces a population that is
**exact on the firm margin and unusable on the employment margin**.
It is retained because the diagnostic is the point: the ratios are
reported per band in ``frame.attrs["employment_coverage"]`` rather
than silently raked away. Closing the gap needs a size-measure
correction or a sponsorship-propensity model, not a second raking
step, and that is a design question for the referee round — raking to
both margins would hide a definitional and selection problem inside a
weight.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..data.form5500 import read_sponsors
from .banding import CANONICAL_BANDS, susb_entrsize_to_canonical
from .targets import load_susb_sector_size

__all__ = [
    "CELL_KEYS",
    "susb_cell_targets",
    "sponsor_frame",
    "post_stratify",
    "calibrate_dual_margin",
    "band_agreement_reference",
]

#: The post-stratification cell: NAICS sector x canonical firm-size band.
CELL_KEYS = ("naics_sector", "canonical_band")

_BAND_ORDER = [band.name for band in CANONICAL_BANDS]


def susb_cell_targets(path: str | None = None) -> pd.DataFrame:
    """SUSB firm counts and employment per sector x canonical band.

    Built from the *detail* enterprise-size classes only — the canonical
    edges were chosen so every detail class nests exactly in one band,
    so no straddling allocation is needed. Total and subtotal rows
    (``ENTRSIZE`` 01/33/37) and the all-sector ``--`` margin are
    dropped; including either would double-count.
    """
    susb = load_susb_sector_size(path)
    susb = susb[susb["naics_sector"] != "--"].copy()
    spans = susb["entrsize_code"].map(susb_entrsize_to_canonical)
    susb = susb[spans.notna()].copy()
    susb["canonical_band"] = [span.band.name for span in spans[spans.notna()]]
    # SUSB publishes combined sector ranges such as "31-33"; the first
    # two digits are the sector key both sides join on.
    susb["naics_sector"] = susb["naics_sector"].astype(str).str[:2]
    out = (
        susb.groupby(list(CELL_KEYS))[["firms", "employment"]]
        .sum()
        .reset_index()
    )
    return out[out["firms"] > 0].reset_index(drop=True)


def sponsor_frame(year: int, data_dir: Path | None = None) -> pd.DataFrame:
    """Observed Form 5500 sponsor records, keyed to the SUSB cell.

    One row per sponsor EIN. Sponsors whose business code does not
    yield a usable NAICS sector are dropped rather than pooled into an
    "unknown" cell, because an unknown-sector row cannot be weighted to
    any SUSB target and would silently dilute whichever cell absorbed
    it. The count dropped is recorded on the returned frame.
    """
    sponsors = read_sponsors(year, data_dir)
    usable = sponsors["naics_sector"].notna()
    frame = sponsors[usable].reset_index(drop=True).copy()
    frame.attrs["dropped_unknown_sector"] = int((~usable).sum())
    return frame


def post_stratify(
    frame: pd.DataFrame,
    targets: pd.DataFrame | None = None,
    *,
    require_full_coverage: bool = True,
) -> pd.DataFrame:
    """Attach cell weights so weighted firm counts match SUSB exactly.

    ``weight = SUSB firms in cell / observed records in cell``. Every
    record in a cell carries the same weight; the weighted count then
    reproduces the SUSB firm margin in that cell by construction.

    ``require_full_coverage`` (default True) makes an **empty target
    cell a hard error**. No weight can populate a stratum with zero
    observed records, so silently returning a frame that under-counts
    a whole sector x band cell would produce a population that looks
    calibrated and is not. Set it False only to inspect a deliberately
    partial frame.

    Diagnostics are attached to ``result.attrs``:

    ``weighted_firms`` / ``target_firms``
        totals, equal by construction when coverage is full.
    ``employment_coverage``
        per band, weighted active participants against SUSB
        employment. Measured at **1.07-2.61, total 2.06x** on the 2023
        files — the naive design overshoots employment badly because
        plan sponsors are the larger firms within any band (module
        docstring). Reported, never corrected: a caller that needs a
        usable employment margin must address the size measure, not
        rake this away.
    ``uncovered_cells``
        target cells with no observed record, empty when coverage is
        full.
    """
    if targets is None:
        targets = susb_cell_targets()
    for column in CELL_KEYS:
        if column not in frame.columns:
            raise ValueError(f"Frame lacks {column!r}; use sponsor_frame().")

    observed = (
        frame.groupby(list(CELL_KEYS)).size().rename("records").reset_index()
    )
    merged = targets.merge(observed, on=list(CELL_KEYS), how="left")
    merged["records"] = merged["records"].fillna(0).astype(int)

    uncovered = merged[merged["records"] == 0]
    if require_full_coverage and not uncovered.empty:
        raise ValueError(
            f"{len(uncovered)} SUSB target cell(s) have no observed "
            "record; no weight can populate an empty stratum. Cells: "
            + ", ".join(
                f"{row.naics_sector}/{row.canonical_band}"
                for row in uncovered.itertuples()
            )
        )

    merged["weight"] = merged["firms"] / merged["records"].where(
        merged["records"] > 0
    )
    out = frame.merge(
        merged[[*CELL_KEYS, "weight", "firms", "employment"]],
        on=list(CELL_KEYS),
        how="left",
    )
    # A sponsor in a cell SUSB does not publish has no target and is
    # given zero weight rather than being dropped: keeping the row
    # makes the exclusion visible in the frame instead of silently
    # shrinking it.
    out["weight"] = out["weight"].fillna(0.0)

    coverage = []
    for band in _BAND_ORDER:
        rows = out[out["canonical_band"] == band]
        target_emp = targets.loc[
            targets["canonical_band"] == band, "employment"
        ].sum()
        weighted_participants = float(
            (rows["active_participants"] * rows["weight"]).sum()
        )
        coverage.append(
            {
                "band": band,
                "weighted_active_participants": weighted_participants,
                "susb_employment": int(target_emp),
                "ratio": (
                    weighted_participants / target_emp if target_emp else None
                ),
            }
        )

    out.attrs["weighted_firms"] = float(out["weight"].sum())
    out.attrs["target_firms"] = int(targets["firms"].sum())
    out.attrs["employment_coverage"] = coverage
    out.attrs["uncovered_cells"] = [
        f"{row.naics_sector}/{row.canonical_band}"
        for row in uncovered.itertuples()
    ]
    return out


def _cell_weights(sizes, target_firms: float, target_employment: float):
    """Maximum-entropy weights matching a cell's firm and size margins.

    Solves ``w_i = exp(l * (p_i - mean))`` scaled so ``sum(w) ==
    target_firms`` and ``sum(w * p) == target_employment``. The
    exponential tilt keeps every weight strictly positive, which a
    linear calibration does not guarantee.

    Returns ``(weights, None)`` on success, or ``(None, reason)`` when
    the target mean lies outside the observed support — no reweighting
    of the observed records can reach a mean they do not bracket.
    """
    import numpy as np

    sizes = np.asarray(sizes, dtype=float)
    if target_firms <= 0 or len(sizes) == 0:
        return None, "empty cell or non-positive firm target"
    target_mean = target_employment / target_firms
    if not (sizes.min() <= target_mean <= sizes.max()):
        return None, (
            f"target mean {target_mean:.1f} outside observed support "
            f"[{sizes.min():.0f}, {sizes.max():.0f}]"
        )
    tilt = 0.0
    for _ in range(200):
        weights = np.exp(tilt * (sizes - target_mean))
        total = weights.sum()
        mean = (weights * sizes).sum() / total
        variance = (weights * sizes * sizes).sum() / total - mean * mean
        if variance <= 0:
            break
        step = (target_mean - mean) / variance
        tilt += step
        if abs(step) < 1e-12:
            break
    weights = np.exp(tilt * (sizes - target_mean))
    return weights * (target_firms / weights.sum()), None


def calibrate_dual_margin(
    frame: pd.DataFrame,
    targets: pd.DataFrame | None = None,
    *,
    size_column: str = "active_participants",
) -> pd.DataFrame:
    """Weight records to match SUSB firm **and** employment margins.

    :func:`post_stratify` matches firm counts only, which overshoots
    employment by 2.06x (module docstring) because a single weight per
    cell treats a 307,086-participant enterprise as representative of
    twenty ordinary ``500+`` firms. Stratifying more finely does not
    help — it makes the ratio worse (2.52), because SUSB's top class is
    also unbounded. The fix is to let weights vary *within* a cell so
    both margins can be met at once.

    On the 2023 files this lands the weighted employment ratio at
    **0.973** with 92 of 97 cells calibrated.

    **The five failures are a SUSB data-quality artifact, not a
    modelling one, and they fail closed.** SUSB infuses noise into
    published employment, and in thin cells the distortion is extreme:
    NAICS 11's ``2,000-2,499`` class reports 5 firms and 292 employees
    (flag ``H``), and its ``5,000+`` class 28 firms and 6,778 (flag
    ``J``). Both are arithmetically impossible for their own size
    class. Where the implied cell mean falls outside the band it
    belongs to, no reweighting can reach it, so the cell is reported in
    ``attrs["infeasible_cells"]`` with its reason and given zero weight
    rather than being forced.
    """
    if targets is None:
        targets = susb_cell_targets()
    if size_column not in frame.columns:
        raise ValueError(f"Frame lacks {size_column!r}; use sponsor_frame().")

    weights = pd.Series(0.0, index=frame.index)
    infeasible: list[dict[str, object]] = []
    calibrated = 0
    indexed = targets.set_index(list(CELL_KEYS))
    for cell, group in frame.groupby(list(CELL_KEYS)):
        if cell not in indexed.index:
            continue
        row = indexed.loc[cell]
        cell_weights, reason = _cell_weights(
            group[size_column].to_numpy(),
            float(row["firms"]),
            float(row["employment"]),
        )
        if cell_weights is None:
            infeasible.append(
                {
                    "cell": "/".join(cell),
                    "reason": reason,
                    "susb_firms": int(row["firms"]),
                    "susb_employment": int(row["employment"]),
                }
            )
            continue
        weights.loc[group.index] = cell_weights
        calibrated += 1

    out = frame.copy()
    out["weight"] = weights
    weighted_employment = float((out[size_column] * out["weight"]).sum())
    out.attrs["calibrated_cells"] = calibrated
    out.attrs["infeasible_cells"] = infeasible
    out.attrs["weighted_firms"] = float(out["weight"].sum())
    out.attrs["target_firms"] = int(targets["firms"].sum())
    out.attrs["weighted_employment"] = weighted_employment
    out.attrs["target_employment"] = int(targets["employment"].sum())
    out.attrs["employment_ratio"] = (
        weighted_employment / targets["employment"].sum()
    )
    return out


def band_agreement_reference(
    sponsors: pd.DataFrame, establishments: pd.DataFrame
) -> dict[str, object]:
    """Cross-source band agreement — a measurement floor, not a gate.

    Joins Form 5500 sponsors to OSHA ITA establishments on EIN (OSHA
    establishments summed to the EIN) and reports how often the two
    *administrative* firm-size measures land in the same canonical
    band. On the 2023/2025 vintages that rate is 66.3% over 43,001
    shared EINs.

    The number bounds how tightly any firm-size gate can be set: a
    threshold finer than the agreement rate between two administrative
    instruments is finer than the instruments resolve. It is evidence
    for the floor batteries and is deliberately **not** used to
    reweight or correct either source, which measure different units.
    """
    if "canonical_band" not in establishments.columns:
        raise ValueError(
            "Establishments lack 'canonical_band'; pass the output of "
            "osha_ita.apply_quality_rule()."
        )
    left = sponsors.set_index("sponsor_ein")["canonical_band"]
    right = (
        establishments.dropna(subset=["ein"])
        .groupby("ein")["annual_average_employees"]
        .sum()
    )
    from .banding import band_of_count

    right_bands = right[right >= 1].map(lambda n: band_of_count(int(n)).name)
    joined = pd.concat(
        [left.rename("sponsor_band"), right_bands.rename("estab_band")],
        axis=1,
        join="inner",
    )
    if joined.empty:
        return {"matched_eins": 0, "agreement_rate": None}
    agree = float((joined["sponsor_band"] == joined["estab_band"]).mean())
    return {
        "matched_eins": int(len(joined)),
        "agreement_rate": agree,
        "confusion": pd.crosstab(
            joined["sponsor_band"], joined["estab_band"]
        ).to_dict(),
    }
