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
    "DEFAULT_WEIGHT_BOUNDS",
    "EMPLOYMENT_OUT_OF_SCOPE_SECTORS",
    "susb_cell_targets",
    "sponsor_frame",
    "post_stratify",
    "calibrate_dual_margin",
    "band_agreement_reference",
]

#: The post-stratification cell: NAICS sector x canonical firm-size band.
CELL_KEYS = ("naics_sector", "canonical_band")

#: Sectors whose sponsor employment is **already counted elsewhere** and
#: must be excluded from the employment margin.
#:
#: NAICS 55 (Management of Companies and Enterprises) is a holding-company
#: sector: one Form 5500 covers the whole enterprise's workforce, while
#: SUSB attributes those workers to the *operating* sectors and records
#: only head-office staff under 55. Including them double-counts. The
#: effect is not marginal — measured on the 2023 files NAICS 55 yields
#: 42,676,524 weighted employees against SUSB's 3,661,977 (**11.7x**),
#: which is **24% of all weighted employment in the frame**. It is
#: systematic across every band, not a thin-cell artifact::
#:
#:     1-9      1.0x        100-499   6.0x
#:     10-49    2.6x        500+     12.4x
#:     50-99    4.2x
#:
#: These sponsors are kept in the **firm** margin — SUSB does count
#: 25,413 NAICS 55 firms, and the frame reproduces them — but their
#: employment is flagged out of scope rather than summed.
EMPLOYMENT_OUT_OF_SCOPE_SECTORS = frozenset({"55"})

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


def _solve_tilt(sizes, target_mean: float, free) -> float:
    """Exponential-tilt parameter matching ``target_mean`` on ``free``.

    Newton iteration on the tilt: the derivative of the weighted mean
    with respect to the tilt is the weighted variance, so the step is
    ``(target - mean) / variance``.
    """
    import numpy as np

    free_sizes = sizes[free]
    tilt = 0.0
    for _ in range(200):
        weights = np.exp(np.clip(tilt * (free_sizes - target_mean), -700, 700))
        total = weights.sum()
        if total <= 0 or not np.isfinite(total):
            break
        mean = (weights * free_sizes).sum() / total
        variance = (weights * free_sizes**2).sum() / total - mean**2
        if variance <= 0 or not np.isfinite(variance):
            break
        step = (target_mean - mean) / variance
        tilt += step
        if abs(step) < 1e-12:
            break
    return tilt


#: Default weight bounds. An unbounded exponential tilt produced a
#: 3,866 weight next to a 1.3e-08 one in the 35-record NAICS 99
#: (unclassified) cell — a single record standing in for 3,866 firms is
#: not a calibration, it is a leverage point. Bounded calibration is
#: the Deville-Sarndal (1992) remedy the project already cites.
#:
#: 140 is the knee of the measured sensitivity curve, not a guess. The
#: p99 weight is 76.5, so bounds above ~140 never bind and give
#: identical margins; below it the firm margin degrades sharply:
#:
#: ====== ============ ===========
#: bound  firm ratio   emp ratio
#: ====== ============ ===========
#: 50           0.7023      0.9766
#: 100          0.9558      1.0151
#: 120          0.9705      1.0173
#: 130          0.9960      1.0226
#: **140**      0.9988      1.0237
#: 250          0.9988      1.0237
#: 1000         0.9990      1.0237
#: ====== ============ ===========
#:
#: So 140 is the tightest bound that costs nothing on either margin,
#: and it is a referee parameter like the OSHA employment cap, not an
#: implementation default to inherit silently.
DEFAULT_WEIGHT_BOUNDS = (0.1, 140.0)


def _cell_weights(
    sizes,
    target_firms: float,
    target_employment: float,
    bounds: tuple[float, float] | None = DEFAULT_WEIGHT_BOUNDS,
):
    """Bounded maximum-entropy weights for one cell's two margins.

    Solves ``w_i = exp(l * (p_i - mean))`` scaled so ``sum(w) ==
    target_firms`` and ``sum(w * p) == target_employment``. The
    exponential tilt keeps every weight strictly positive, which a
    linear calibration does not guarantee.

    ``bounds`` clips weights to ``[lo, hi]`` and re-solves the tilt on
    the records still free, iterating until the clipped set is stable.
    Because the tilt is monotone in ``p_i``, clipping only ever removes
    the extremes, so the procedure terminates. Bounding trades exactness
    on the employment margin for the absence of leverage points; the
    residual is returned so the caller can report it rather than
    discover it later.

    Returns ``(weights, None, residual)`` on success, or
    ``(None, reason, None)`` when the target mean lies outside the
    observed support — no reweighting of the observed records can reach
    a mean they do not bracket.
    """
    import numpy as np

    sizes = np.asarray(sizes, dtype=float)
    if target_firms <= 0 or len(sizes) == 0:
        return None, "empty cell or non-positive firm target", None
    target_mean = target_employment / target_firms
    if not (sizes.min() <= target_mean <= sizes.max()):
        return (
            None,
            (
                f"target mean {target_mean:.1f} outside observed support "
                f"[{sizes.min():.0f}, {sizes.max():.0f}]"
            ),
            None,
        )

    free = np.ones(len(sizes), dtype=bool)
    weights = np.ones(len(sizes), dtype=float)
    for _ in range(20):
        tilt = _solve_tilt(sizes, target_mean, free)
        # Clip the exponent before exponentiating: a wide cell (500 to
        # 2.5M participants) can overflow float64 mid-solve, and an inf
        # weight silently poisons the rescale to NaN.
        weights = np.exp(np.clip(tilt * (sizes - target_mean), -700, 700))
        weights *= target_firms / weights.sum()
        if bounds is None:
            break
        lo, hi = bounds
        clipped = (weights < lo) | (weights > hi)
        if not clipped.any() or not (free & ~clipped).any():
            break
        weights = np.clip(weights, lo, hi)
        free = ~clipped
    if bounds is not None:
        # Final clip is NOT followed by a rescale. Rescaling to hit the
        # firm total after clipping pushes weights straight back over
        # the bound — that bug left two NAICS 99 records at 4,138 while
        # the bound was nominally 250. The firm-margin residual this
        # leaves is returned instead of being papered over.
        weights = np.clip(weights, *bounds)
    residual = float((weights * sizes).sum() - target_employment)
    firm_residual = float(weights.sum() - target_firms)
    return weights, None, (residual, firm_residual)


def calibrate_dual_margin(
    frame: pd.DataFrame,
    targets: pd.DataFrame | None = None,
    *,
    size_column: str = "active_participants",
    weight_bounds: tuple[float, float] | None = DEFAULT_WEIGHT_BOUNDS,
    firm_only_fallback: bool = True,
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
    residuals: list[dict[str, object]] = []
    calibrated = 0
    firm_only = 0
    indexed = targets.set_index(list(CELL_KEYS))
    for cell, group in frame.groupby(list(CELL_KEYS)):
        if cell not in indexed.index:
            continue
        row = indexed.loc[cell]
        cell_weights, reason, residual = _cell_weights(
            group[size_column].to_numpy(),
            float(row["firms"]),
            float(row["employment"]),
            weight_bounds,
        )
        if cell_weights is None:
            infeasible.append(
                {
                    "cell": "/".join(cell),
                    "reason": reason,
                    "susb_firms": int(row["firms"]),
                    "susb_employment": int(row["employment"]),
                    "firm_margin_held": bool(firm_only_fallback),
                }
            )
            if firm_only_fallback:
                # The employment target is out of scope for this cell
                # (module docstring), but the firm count is sound. Hold
                # the firm margin and drop only the employment
                # constraint, rather than losing the cell's firms.
                #
                # The same bound applies here. NAICS 55's 500+ cell has
                # 7,373 SUSB firms behind very few sponsors, so an
                # unbounded fallback weight reaches 4,138 — a worse
                # leverage point than the one bounding was added to
                # remove. Bounding it under-counts that cell's firms
                # instead, which is recorded rather than hidden.
                flat = float(row["firms"]) / len(group)
                if weight_bounds is not None:
                    flat = min(max(flat, weight_bounds[0]), weight_bounds[1])
                weights.loc[group.index] = flat
                infeasible[-1]["fallback_weight"] = flat
                infeasible[-1]["firms_represented"] = flat * len(group)
                firm_only += 1
            continue
        weights.loc[group.index] = cell_weights
        calibrated += 1
        if residual and any(residual):
            residuals.append(
                {
                    "cell": "/".join(cell),
                    "employment_residual": residual[0],
                    "firm_residual": residual[1],
                }
            )

    out = frame.copy()
    out["weight"] = weights
    weighted_employment = float((out[size_column] * out["weight"]).sum())
    scoped = targets.copy()
    excluded = {entry["cell"] for entry in infeasible}
    # Whole-sector exclusions (NAICS 55) join the cell-level ones, so a
    # downstream consumer cannot accidentally sum double-counted
    # employment: the flag travels on the frame, not just in attrs.
    cell_key = out["naics_sector"] + "/" + out["canonical_band"]
    out["employment_in_scope"] = ~(
        cell_key.isin(excluded)
        | out["naics_sector"].isin(EMPLOYMENT_OUT_OF_SCOPE_SECTORS)
    )
    excluded = excluded | {
        f"{row.naics_sector}/{row.canonical_band}"
        for row in targets.itertuples()
        if row.naics_sector in EMPLOYMENT_OUT_OF_SCOPE_SECTORS
    }
    scoped_key = scoped["naics_sector"] + "/" + scoped["canonical_band"]
    in_scope = scoped[~scoped_key.isin(excluded)]
    out.attrs["calibrated_cells"] = calibrated
    out.attrs["firm_only_cells"] = firm_only
    out.attrs["infeasible_cells"] = infeasible
    out.attrs["weight_bounds"] = weight_bounds
    out.attrs["bounded_cell_residuals"] = residuals
    out.attrs["weighted_firms"] = float(out["weight"].sum())
    out.attrs["target_firms"] = int(targets["firms"].sum())
    out.attrs["weighted_employment"] = weighted_employment
    out.attrs["target_employment"] = int(targets["employment"].sum())
    out.attrs["employment_ratio"] = (
        weighted_employment / targets["employment"].sum()
    )
    # The honest ratio excludes cells whose published employment is out
    # of scope for their own size class; including them compares against
    # a target that cannot be met by construction.
    out.attrs["in_scope_target_employment"] = int(in_scope["employment"].sum())
    in_scope_rows = out[out["employment_in_scope"]]
    out.attrs["in_scope_employment_ratio"] = (
        float((in_scope_rows[size_column] * in_scope_rows["weight"]).sum())
        / in_scope["employment"].sum()
    )
    out.attrs["employment_out_of_scope_sectors"] = sorted(
        EMPLOYMENT_OUT_OF_SCOPE_SECTORS
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
