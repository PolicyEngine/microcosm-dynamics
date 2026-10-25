"""Frozen P2 development law on nominal earnings and exact recent history.

The incumbent owns unchanged rank, donor, marginal, clock and refresh math.
This sibling owns its candidate, fit orchestration, four-feature participation
queries, provenance and restart adapter. It is deliberately outside REGISTRY.
"""

from __future__ import annotations

import hashlib
import inspect
import pickle
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import forward_earnings as v1
from .candidates import CANDIDATE_3, CandidateSpec, OperationSpec
from .forward_earnings import (
    AGE_MAX,
    AGE_MIN,
    BOUNDARY_YEAR,
    FRAME_COLUMNS,
    PERIOD_STEP,
    REFRESH_STATE_COLUMN,
    EarningsGenerationResult,
    ForwardEarningsFit,
    ForwardEarningsGenerator,
    ProjectedWageIndex,
    QRFModelFactory,
    RankRefreshFitAudit,
    _correlated_refresh_threshold,
    _require_columns,
    _substream,
    fit_age_marginals,
    fit_projected_wage_index,
    validate_rank_refresh_fit,
)
from .refit import EarningsChainedRefit, RefitProvenance
from .rng import seed_from_generator

P2_CANDIDATE_SPEC = CandidateSpec(
    candidate_id="m6_candidate3_p2_history_engine_v1",
    contract_revision="p2_frozen_2026_10_22",
    operations=tuple(
        OperationSpec(op.kind, op.implementation_id, op.params)
        for op in CANDIDATE_3.operations
    ),
)
P2_FEATURES = ("earnings", "age_tp2", "prior_positive", "prior_missing")
P2_FIT_PREDICTORS = P2_FEATURES
P2_HISTORY_RULE = {
    "earnings_scale": "nominal",
    "positive_threshold": 1e-6,
    "comparison": ">",
    "lag_years_from_source": 2,
    "history_join": "exact person/year left join; many_to_one",
    "lookup_before_age_filter": True,
    "missing_encoding": [0.0, 1.0],
    "invalid_refusal": "P2_INVALID_HISTORY_VALUE",
}


def history_indicators(older: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Encode available raw history; invalid values abort the operation."""
    older = np.asarray(older, dtype=np.float64)
    if np.any(older < 0) or np.isinf(older).any():
        raise ValueError("P2_INVALID_HISTORY_VALUE")
    missing = np.isnan(older)
    positive = older > 1e-6
    return positive.astype(np.float64), missing.astype(np.float64)


def construct_gate_view(
    pairs: pd.DataFrame, cutoff_panel: pd.DataFrame
) -> pd.DataFrame:
    """Attach history without altering the incumbent raw pair population."""
    history = cutoff_panel.loc[:, ["person_id", "period", "earnings"]].rename(
        columns={"period": "prior_year", "earnings": "prior_earnings"}
    )
    view = pairs.copy()
    view["prior_year"] = view["period"] - PERIOD_STEP
    view = view.merge(
        history,
        on=["person_id", "prior_year"],
        how="left",
        sort=False,
        validate="many_to_one",
    )
    older = view["prior_earnings"].to_numpy(dtype=np.float64)
    positive, missing = history_indicators(older)
    view["history_available"] = ~np.isnan(older)
    view["prior_positive"] = positive
    view["prior_missing"] = missing
    view[list(P2_FEATURES)] = view[list(P2_FEATURES)].astype(np.float64)
    return view


def fit_p2_gate(
    gate_view: pd.DataFrame,
    *,
    seed: int,
    qrf_factory: QRFModelFactory | None = None,
) -> Any:
    """Fit exactly one pinned wrapper, including its normal amount forests."""
    rows = gate_view
    factory = qrf_factory or v1._default_qrf_factory
    return factory(seed=int(seed)).fit(
        rows,
        predictors=list(P2_FIT_PREDICTORS),
        targets=["earnings_tp2"],
        weights="weight_tp2",
    )


def gate_features(
    current: np.ndarray, target_age: np.ndarray, older: np.ndarray
) -> pd.DataFrame:
    """Build the same four ordered float64 predictors for every query."""
    current = np.asarray(current, dtype=np.float64)
    target_age = np.asarray(target_age, dtype=np.float64)
    older = np.asarray(older, dtype=np.float64)
    if current.shape != target_age.shape or current.shape != older.shape:
        raise ValueError("P2 gate query shapes differ")
    positive, missing = history_indicators(older)
    return pd.DataFrame(
        {
            "earnings": current,
            "age_tp2": target_age,
            "prior_positive": positive,
            "prior_missing": missing,
        },
        dtype=np.float64,
    )


def runtime_gate_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Inspect the applicable runtime query without consuming randomness."""
    return gate_features(
        frame["earnings"].to_numpy(dtype=np.float64),
        frame["age"].to_numpy(dtype=np.float64),
        frame["gen_earn_w4"].to_numpy(dtype=np.float64),
    )


def query_gate_probabilities(
    fitted: Any,
    current: np.ndarray,
    target_age: np.ndarray,
    older: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Use the recorded classifier column/class order, including point masses."""
    features = gate_features(current, target_age, older)
    target = fitted._target_models["earnings_tp2"]
    if target.gate is None:
        signs = {"positive_only": 1, "negative_only": -1, "degenerate_zero": 0}
        sign = signs[target.regime]
        return np.asarray([sign], dtype=np.int64), np.ones((len(features), 1))
    values = features.loc[:, list(target.columns)].to_numpy(dtype=np.float64)
    classes = np.asarray(target.gate.classes_)
    probabilities = np.asarray(target.gate.predict_proba(values))
    return classes, probabilities


def draw_p2_sign(
    fitted: Any,
    current: np.ndarray,
    target_age: np.ndarray,
    older: np.ndarray,
    uniforms: np.ndarray,
) -> np.ndarray:
    """Apply the inherited cumulative >= selection to the shared distribution."""
    classes, probabilities = query_gate_probabilities(
        fitted, current, target_age, older
    )
    cumulative = np.cumsum(probabilities, axis=1)
    selected = (cumulative >= np.asarray(uniforms)[:, None]).argmax(axis=1)
    return classes[selected]


@dataclass(frozen=True)
class P2ForwardEarningsFit(ForwardEarningsFit):
    """Auditable raw pairs, separate gate view and admitted-state signatures."""

    gate_view: pd.DataFrame = field(default_factory=pd.DataFrame)
    cutoff_panel: pd.DataFrame = field(default_factory=pd.DataFrame)
    fit_signature: Mapping[str, Any] = field(default_factory=dict)
    zero_anchor_gate_removed: bool = True


def _bytes_sha256(array: Any, dtype: str) -> str:
    values = np.ascontiguousarray(np.asarray(array, dtype=dtype))
    digest = hashlib.sha256()
    digest.update(dtype.encode())
    digest.update(np.asarray(values.shape, dtype="<i8").tobytes())
    digest.update(values.tobytes())
    return digest.hexdigest()


def unchanged_component_checksums(
    generator: ForwardEarningsGenerator,
    estimation: pd.DataFrame,
    pairs: pd.DataFrame,
    anchors: pd.DataFrame,
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Hash the inherited components separately from both participation gates."""
    return {
        "estimation": v1._frame_checksum(
            estimation, ("person_id", "period", "earnings", "age", "weight")
        ),
        "pairs": v1._frame_checksum(
            pairs,
            (
                "person_id",
                "period",
                "period_tp2",
                "earnings",
                "earnings_tp2",
                "age",
                "age_tp2",
                "weight",
                "weight_tp2",
            ),
        ),
        "anchors": v1._frame_checksum(
            anchors, ("person_id", "period", "earnings", "age", "weight")
        ),
        "boundary_map": v1._canonical_sha256(
            generator.realized_earn_2014_by_person
        ),
        "history_map": v1._canonical_sha256(
            generator.realized_earn_2012_by_person
        ),
        "marginals": v1._canonical_sha256(
            {
                str(index): {
                    "p0": cell.p0,
                    "wtil": cell.wtil,
                    "yval": cell.yval,
                    "n_pos": cell.n_pos,
                    "w_total": cell.w_total,
                }
                for index, cell in generator.marginals.items()
            }
        ),
        "permanent_scores": v1._canonical_sha256(generator.u_w_by_person),
        "permanent_diagnostics": v1._canonical_sha256(diagnostics),
        "pools": {
            name: v1._array_mapping_checksum(pool)
            for name, pool in generator.pools.items()
        },
        "stable_pools": (
            None
            if generator.stable_pools is None
            else {
                str(index): v1._array_mapping_checksum(pool)
                for index, pool in generator.stable_pools.items()
            }
        ),
        "refresh_audit": (
            None
            if generator.rank_refresh_fit_audit is None
            else generator.rank_refresh_fit_audit.as_dict()
        ),
        "refresh_q": generator.rank_refresh_q,
        "refresh_rho": generator.rank_refresh_rho,
        "wage_index": v1._canonical_sha256(
            {
                "actual": generator.wage_index.actual,
                "intercept": generator.wage_index.intercept,
                "slope": generator.wage_index.slope,
                "boundary_year": generator.wage_index.boundary_year,
            }
        ),
    }


def _p2_fit_signature(
    generator: ForwardEarningsGenerator,
    estimation: pd.DataFrame,
    pairs: pd.DataFrame,
    anchors: pd.DataFrame,
    diagnostics: Mapping[str, Any],
    gate_view: pd.DataFrame,
    seed: int,
    factory: QRFModelFactory,
) -> dict[str, Any]:
    ordered = gate_view.sort_values(["person_id", "period_tp2"], kind="stable")
    older = ordered["prior_earnings"].to_numpy(dtype=np.float64)
    available = ordered["history_available"].to_numpy(dtype=bool)
    classes, probabilities = query_gate_probabilities(
        generator.shared_gate,
        ordered["earnings"].to_numpy(),
        ordered["age_tp2"].to_numpy(),
        older,
    )
    estimator = factory(seed=int(seed))
    target = generator.shared_gate._target_models["earnings_tp2"]
    source_paths = {
        "p2": Path(__file__),
        "v1": Path(v1.__file__),
        "estimator": Path(inspect.getfile(type(estimator))),
        **{
            name: Path(__file__).with_name(f"{name}.py")
            for name in (
                "candidates",
                "refit",
                "earnings_domain",
                "rng",
                "steps",
                "loop",
                "support",
            )
        },
    }
    return {
        "candidate": P2_CANDIDATE_SPEC.canonical_dict(),
        "seed": int(seed),
        "boundary": int(generator.boundary_year),
        "dependencies": {
            name: version(name)
            for name in (
                "numpy",
                "pandas",
                "scipy",
                "scikit-learn",
                "populace-fit",
            )
        },
        "sources": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in source_paths.items()
        },
        "estimator_parameters": vars(estimator),
        "classifier_parameters": (
            None if target.gate is None else target.gate.get_params()
        ),
        "features": list(P2_FEATURES),
        "dtype": "float64",
        "history_rule": P2_HISTORY_RULE,
        "canonical_feature_sha256": _bytes_sha256(
            ordered[list(P2_FEATURES)], "<f8"
        ),
        "pair_keys_sha256": _bytes_sha256(
            ordered[["person_id", "period", "period_tp2"]], "<i8"
        ),
        "lookup_year_sha256": _bytes_sha256(ordered["prior_year"], "<i8"),
        "availability_sha256": _bytes_sha256(available, "|b1"),
        "history_values_sha256": _bytes_sha256(
            np.where(available, older, 0.0), "<f8"
        ),
        "raw_target_sha256": _bytes_sha256(ordered["earnings_tp2"], "<f8"),
        "target_weights_sha256": _bytes_sha256(ordered["weight_tp2"], "<f8"),
        "classes": classes.tolist(),
        "probability_shape": list(probabilities.shape),
        "probabilities_sha256": _bytes_sha256(probabilities, "<f8"),
        "serialized_gate_protocol": 5,
        "serialized_gate_sha256": hashlib.sha256(
            pickle.dumps(generator.shared_gate, protocol=5)
        ).hexdigest(),
        "gate_count": 1,
        "zero_anchor_gate": None,
        "zero_anchor_gate_removed": True,
        "n_zero_anchor_pairs": 0,
        "component_checksums": unchanged_component_checksums(
            generator, estimation, pairs, anchors, diagnostics
        ),
    }


def fit_forward_earnings_p2_v1(
    panel: pd.DataFrame,
    nawi: Mapping[int, float],
    *,
    seed: int,
    boundary_year: int = BOUNDARY_YEAR,
    qrf_factory: QRFModelFactory | None = None,
) -> P2ForwardEarningsFit:
    """Fit the pinned forward gates, rank pools, marginals, and frame state."""
    candidate_spec = P2_CANDIDATE_SPEC
    rank_refresh_q = v1._rank_refresh_probability(candidate_spec)
    rank_refresh_rho = v1._rank_refresh_correlation(candidate_spec)
    _require_columns(
        panel,
        ("person_id", "period", "earnings", "age", "weight"),
        "earnings panel",
    )
    period = pd.to_numeric(panel["period"], errors="raise")
    cutoff_panel = panel.loc[
        (period <= boundary_year) & (panel["weight"] > 0)
    ].copy()
    cutoff_panel = cutoff_panel.sort_values(
        ["person_id", "period"]
    ).reset_index(drop=True)
    if cutoff_panel.duplicated(["person_id", "period"]).any():
        raise ValueError("earnings panel has duplicate person-period rows")
    estimation = cutoff_panel.loc[
        cutoff_panel["age"].between(AGE_MIN, AGE_MAX)
    ].copy()
    estimation = estimation.sort_values(["person_id", "period"]).reset_index(
        drop=True
    )
    if estimation.empty:
        raise ValueError("forward earnings refit has no admissible rows")
    actual_index = v1._precutoff_nawi(
        cutoff_panel, nawi, boundary_year=boundary_year
    )
    wage_projection = fit_projected_wage_index(
        nawi, boundary_year=boundary_year
    )
    wage_projection = ProjectedWageIndex(
        actual=actual_index,
        intercept=wage_projection.intercept,
        slope=wage_projection.slope,
        boundary_year=boundary_year,
    )
    marginals = fit_age_marginals(estimation, actual_index)
    u_w_by_person, u_w_diagnostics = v1._fit_u_w(
        estimation, marginals, actual_index
    )

    anchors = cutoff_panel[cutoff_panel["period"] == boundary_year][
        ["person_id", "period", "earnings", "age", "weight"]
    ].copy()
    if anchors["person_id"].duplicated().any():
        raise ValueError("forward earnings fit has duplicate 2014 anchors")
    anchor_ids = set(anchors["person_id"].astype(int))
    if not anchor_ids:
        raise ValueError("forward earnings fit has no realized-2014 anchors")
    u_w_by_person = {
        person_id: float(u_w_by_person.get(person_id, 0.5))
        for person_id in anchor_ids
    }
    pairs = v1._forward_pairs(estimation)
    pairs = pairs[pairs["person_id"].isin(anchor_ids)].reset_index(drop=True)
    if pairs.empty:
        raise ValueError(
            "forward earnings refit has no adjacent biennial pairs"
        )

    factory = qrf_factory or v1._default_qrf_factory
    gate_view = construct_gate_view(pairs, cutoff_panel)
    shared_gate = fit_p2_gate(gate_view, seed=seed, qrf_factory=factory)
    zero_gate = None
    pools = v1._build_donor_pools(
        estimation,
        pairs,
        anchors,
        marginals,
        actual_index,
        u_w_by_person,
    )
    stable_pools: Mapping[int, Mapping[str, np.ndarray]] | None = None
    refresh_audit: RankRefreshFitAudit | None = None
    if rank_refresh_q is not None:
        stable_pools, refresh_audit = v1._build_stable_pools(
            pairs, pools["pairs"]
        )

    realized_2014 = {
        int(row.person_id): float(row.earnings)
        for row in anchors.itertuples(index=False)
    }
    rows_2012 = cutoff_panel[
        cutoff_panel["period"] == boundary_year - PERIOD_STEP
    ]
    realized_2012 = {
        int(row.person_id): float(row.earnings)
        for row in rows_2012.itertuples(index=False)
    }
    generator = P2ForwardEarningsGeneratorV1(
        shared_gate=shared_gate,
        zero_anchor_gate=zero_gate,
        marginals=marginals,
        pools=pools,
        wage_index=wage_projection,
        u_w_by_person=u_w_by_person,
        realized_earn_2014_by_person=realized_2014,
        realized_earn_2012_by_person=realized_2012,
        boundary_year=boundary_year,
        rank_refresh_q=rank_refresh_q,
        stable_pools=stable_pools,
        rank_refresh_fit_audit=refresh_audit,
        rank_refresh_rho=rank_refresh_rho,
    )
    fit_signature = _p2_fit_signature(
        generator,
        estimation,
        pairs,
        anchors,
        u_w_diagnostics,
        gate_view,
        seed,
        factory,
    )
    return P2ForwardEarningsFit(
        generator=generator,
        estimation_panel=estimation,
        forward_pairs=pairs,
        anchors=anchors.reset_index(drop=True),
        n_zero_anchor_pairs=0,
        u_w_diagnostics=u_w_diagnostics,
        rank_refresh_fit_audit=refresh_audit,
        q_invariant_fit_signature_sha256=v1._canonical_sha256(fit_signature),
        gate_view=gate_view,
        cutoff_panel=cutoff_panel,
        fit_signature=fit_signature,
        zero_anchor_gate_removed=True,
    )


@dataclass(frozen=True)
class P2ForwardEarningsGeneratorV1(ForwardEarningsGenerator):
    """Inherited donor law with P2's single recent-history participation gate.

    The two generation bodies preserve incumbent validation, substreams and
    branch order. Only participation queries differ. All other methods are
    inherited unchanged; no incumbent module globals are replaced.
    """

    def _draw_participation(
        self,
        current: np.ndarray,
        target_age: np.ndarray,
        older: np.ndarray,
        uniforms: np.ndarray,
    ) -> np.ndarray:
        return draw_p2_sign(
            self.shared_gate, current, target_age, older, uniforms
        )

    def generate_with_frame_updates(
        self, frame: pd.DataFrame, year: int, rng: np.random.Generator
    ) -> EarningsGenerationResult:
        """Draw the correlated prototype and return its generated-lag state."""
        if self.rank_refresh_rho is None:
            raise ValueError(
                "frame-update generation requires a bound rank-refresh rho"
            )
        year = int(year)
        if year % PERIOD_STEP:
            _require_columns(
                frame,
                ("earnings", "age", REFRESH_STATE_COLUMN),
                "forward earnings frame",
            )
            state = frame[REFRESH_STATE_COLUMN].to_numpy(
                dtype=np.float64, copy=True
            )
            _correlated_refresh_threshold(
                float(self.rank_refresh_q),
                self.rank_refresh_rho,
                state,
            )
            age = frame["age"].to_numpy(dtype=np.float64)
            level = frame["earnings"].to_numpy(dtype=np.float64, copy=True)
            state[(level <= 0.0) | (age < AGE_MIN) | (age > AGE_MAX)] = np.nan
            return EarningsGenerationResult(
                earnings=level,
                frame_updates={REFRESH_STATE_COLUMN: state},
            )
        if year <= self.boundary_year:
            raise ValueError("forward earnings even draws begin after 2014")
        validate_rank_refresh_fit(self)
        _require_columns(
            frame,
            (*FRAME_COLUMNS, REFRESH_STATE_COLUMN),
            "forward earnings frame",
        )

        conditioning = frame.loc[:, [*FRAME_COLUMNS, REFRESH_STATE_COLUMN]]
        order = np.argsort(
            conditioning["person_id"].to_numpy(dtype=np.int64), kind="stable"
        )
        inverse = np.empty(len(order), dtype=np.int64)
        inverse[order] = np.arange(len(order))
        sorted_frame = conditioning.iloc[order]
        current_age = sorted_frame["age"].to_numpy(dtype=np.float64)
        current_level = sorted_frame["earnings"].to_numpy(dtype=np.float64)
        lag_level = sorted_frame["gen_earn_w2"].to_numpy(dtype=np.float64)
        prior_level = sorted_frame["gen_earn_w4"].to_numpy(dtype=np.float64)
        anchor_level = sorted_frame["realized_earn_2014"].to_numpy(
            dtype=np.float64
        )
        previous_state = sorted_frame[REFRESH_STATE_COLUMN].to_numpy(
            dtype=np.float64
        )
        _correlated_refresh_threshold(
            float(self.rank_refresh_q),
            self.rank_refresh_rho,
            previous_state,
        )
        target_u_w = sorted_frame["u_w"].to_numpy(dtype=np.float64)
        if (
            not np.isfinite(target_u_w).all()
            or sorted_frame["sex"].isna().any()
        ):
            raise ValueError("forward earnings frame has invalid u_w or sex")
        required_numeric = np.column_stack(
            (current_age, current_level, lag_level, anchor_level)
        )
        history_indicators(prior_level)
        prior_invalid = (
            np.any(prior_level < 0)
            or np.isinf(prior_level).any()
            or (
                year >= self.boundary_year + 2 * PERIOD_STEP
                and np.isnan(prior_level).any()
            )
        )
        if (
            not np.isfinite(required_numeric).all()
            or np.any(required_numeric[:, 1:] < 0)
            or prior_invalid
        ):
            raise ValueError(
                "forward earnings frame has invalid numeric state"
            )

        seed = seed_from_generator(rng)
        gate_rng = _substream(seed, "gate")
        donor_rng = _substream(seed, "donor-draw")
        reentry_rng = _substream(seed, "re-entry-draw")
        refresh_gate_rng = _substream(seed, "memory-refresh-gate")
        refresh_rank_rng = _substream(seed, "memory-refresh-rank")

        anchor_rank = self._anchor_ranks(anchor_level, current_age, year)
        q0 = anchor_level == 0
        gate_uniform = gate_rng.random(len(sorted_frame))
        signs = self._draw_participation(
            current_level,
            current_age,
            prior_level,
            gate_uniform,
        )

        generated = np.zeros(len(sorted_frame), dtype=np.float64)
        next_state = np.full(len(sorted_frame), np.nan, dtype=np.float64)
        participating = np.flatnonzero(signs == 1)
        if len(participating):
            current_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            current_positive = lag_level > 0
            current_indices = np.flatnonzero(current_positive)
            if len(current_indices):
                current_rank[current_indices] = self.level_to_rank(
                    lag_level[current_indices],
                    current_age[current_indices] - PERIOD_STEP,
                    year - PERIOD_STEP,
                )

            prior_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            prior_positive = prior_level > 0
            prior_indices = np.flatnonzero(prior_positive)
            if len(prior_indices):
                prior_rank[prior_indices] = self.level_to_rank(
                    prior_level[prior_indices],
                    current_age[prior_indices] - 2 * PERIOD_STEP,
                    year - 2 * PERIOD_STEP,
                )

            output_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            reentry = participating[~current_positive[participating]]
            triple = participating[
                current_positive[participating]
                & prior_positive[participating]
                & (year >= self.boundary_year + 2 * PERIOD_STEP)
            ]
            pair = participating[
                current_positive[participating]
                & ~np.isin(participating, triple)
            ]

            self._draw_reentry(
                reentry, q0, anchor_rank, reentry_rng, output_rank
            )
            self._draw_transition(
                triple,
                q0,
                current_rank,
                prior_rank,
                anchor_rank,
                donor_rng,
                output_rank,
                triple=True,
            )
            self._draw_transition(
                pair,
                q0,
                current_rank,
                prior_rank,
                anchor_rank,
                donor_rng,
                output_rank,
                triple=False,
            )
            continuers = participating[current_positive[participating]]
            effective_state = previous_state.copy()
            in_support = (current_age >= AGE_MIN) & (current_age <= AGE_MAX)
            effective_state[~in_support] = np.nan
            refreshed = self._draw_correlated_rank_refresh(
                continuers,
                q0,
                anchor_rank,
                current_age,
                effective_state,
                refresh_gate_rng,
                refresh_rank_rng,
                output_rank,
            )
            carried = in_support[continuers]
            next_state[continuers[carried]] = refreshed[carried].astype(
                np.float64
            )
            generated[participating] = self.rank_to_level(
                output_rank[participating], current_age[participating], year
            )
        return EarningsGenerationResult(
            earnings=generated[inverse],
            frame_updates={REFRESH_STATE_COLUMN: next_state[inverse]},
        )

    def generate(
        self, frame: pd.DataFrame, year: int, rng: np.random.Generator
    ) -> np.ndarray:
        """Draw one projection year's levels, with no RNG use on odd years."""
        if self.rank_refresh_rho is not None:
            raise ValueError(
                "correlated refresh requires generate_with_frame_updates"
            )
        year = int(year)
        if year % PERIOD_STEP:
            _require_columns(frame, ("earnings",), "forward earnings frame")
            return frame["earnings"].to_numpy(dtype=np.float64, copy=True)
        if year <= self.boundary_year:
            raise ValueError("forward earnings even draws begin after 2014")
        validate_rank_refresh_fit(self)
        _require_columns(frame, FRAME_COLUMNS, "forward earnings frame")

        # Select only the pinned conditioning surface.  In particular, this
        # intentionally never asks pandas for the frame's realized ``nawi``.
        conditioning = frame.loc[:, list(FRAME_COLUMNS)]
        order = np.argsort(
            conditioning["person_id"].to_numpy(dtype=np.int64), kind="stable"
        )
        inverse = np.empty(len(order), dtype=np.int64)
        inverse[order] = np.arange(len(order))
        sorted_frame = conditioning.iloc[order]
        current_age = sorted_frame["age"].to_numpy(dtype=np.float64)
        current_level = sorted_frame["earnings"].to_numpy(dtype=np.float64)
        lag_level = sorted_frame["gen_earn_w2"].to_numpy(dtype=np.float64)
        prior_level = sorted_frame["gen_earn_w4"].to_numpy(dtype=np.float64)
        anchor_level = sorted_frame["realized_earn_2014"].to_numpy(
            dtype=np.float64
        )
        # Schema validation reads u_w and sex, while the pinned donor-side
        # lambda law correctly leaves both out of target distances.
        target_u_w = sorted_frame["u_w"].to_numpy(dtype=np.float64)
        if (
            not np.isfinite(target_u_w).all()
            or sorted_frame["sex"].isna().any()
        ):
            raise ValueError("forward earnings frame has invalid u_w or sex")
        required_numeric = np.column_stack(
            (current_age, current_level, lag_level, anchor_level)
        )
        history_indicators(prior_level)
        prior_invalid = (
            np.any(prior_level < 0)
            or np.isinf(prior_level).any()
            or (
                year >= self.boundary_year + 2 * PERIOD_STEP
                and np.isnan(prior_level).any()
            )
        )
        if (
            not np.isfinite(required_numeric).all()
            or np.any(required_numeric[:, 1:] < 0)
            or prior_invalid
        ):
            raise ValueError(
                "forward earnings frame has invalid numeric state"
            )

        seed = seed_from_generator(rng)
        gate_rng = _substream(seed, "gate")
        donor_rng = _substream(seed, "donor-draw")
        reentry_rng = _substream(seed, "re-entry-draw")
        refresh_gate_rng = None
        refresh_rank_rng = None
        if self.rank_refresh_q is not None:
            refresh_gate_rng = _substream(seed, "memory-refresh-gate")
            refresh_rank_rng = _substream(seed, "memory-refresh-rank")

        anchor_rank = self._anchor_ranks(anchor_level, current_age, year)
        q0 = anchor_level == 0
        gate_uniform = gate_rng.random(len(sorted_frame))
        signs = self._draw_participation(
            current_level,
            current_age,
            prior_level,
            gate_uniform,
        )

        generated = np.zeros(len(sorted_frame), dtype=np.float64)
        participating = np.flatnonzero(signs == 1)
        if len(participating):
            current_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            current_positive = lag_level > 0
            current_indices = np.flatnonzero(current_positive)
            if len(current_indices):
                current_rank[current_indices] = self.level_to_rank(
                    lag_level[current_indices],
                    current_age[current_indices] - PERIOD_STEP,
                    year - PERIOD_STEP,
                )

            prior_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            prior_positive = prior_level > 0
            prior_indices = np.flatnonzero(prior_positive)
            if len(prior_indices):
                prior_rank[prior_indices] = self.level_to_rank(
                    prior_level[prior_indices],
                    current_age[prior_indices] - 2 * PERIOD_STEP,
                    year - 2 * PERIOD_STEP,
                )

            output_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            reentry = participating[~current_positive[participating]]
            triple = participating[
                current_positive[participating]
                & prior_positive[participating]
                & (year >= self.boundary_year + 2 * PERIOD_STEP)
            ]
            pair = participating[
                current_positive[participating]
                & ~np.isin(participating, triple)
            ]

            # Candidate-10's frozen branch/subset draw order.
            self._draw_reentry(
                reentry, q0, anchor_rank, reentry_rng, output_rank
            )
            self._draw_transition(
                triple,
                q0,
                current_rank,
                prior_rank,
                anchor_rank,
                donor_rng,
                output_rank,
                triple=True,
            )
            self._draw_transition(
                pair,
                q0,
                current_rank,
                prior_rank,
                anchor_rank,
                donor_rng,
                output_rank,
                triple=False,
            )
            if self.rank_refresh_q is not None:
                assert refresh_gate_rng is not None
                assert refresh_rank_rng is not None
                continuers = participating[current_positive[participating]]
                self._draw_rank_refresh(
                    continuers,
                    q0,
                    anchor_rank,
                    current_age,
                    refresh_gate_rng,
                    refresh_rank_rng,
                    output_rank,
                )
            generated[participating] = self.rank_to_level(
                output_rank[participating], current_age[participating], year
            )
        return generated[inverse]


P2_REFIT_SPEC = {
    "candidate": "m6_candidate3_p2_history_engine_v1",
    "contract_revision": "p2_frozen_2026_10_22",
    "gate_count": 1,
    "zero_anchor_gate_removed": True,
    "shared_qrf": {
        "implementation": "populace.fit.qrf.RegimeGatedQRF",
        "parameters": "defaults; seed only",
        "predictors": [
            "earnings",
            "age_tp2",
            "prior_positive",
            "prior_missing",
        ],
        "target": "earnings_tp2",
        "weight": "weight_tp2",
    },
    "source_scale": "nominal",
    "history": {
        "lag_years_from_source": 2,
        "positive_threshold": 1e-6,
        "comparison": ">",
        "missing_encoding": [0.0, 1.0],
        "invalid_refusal": "P2_INVALID_HISTORY_VALUE",
        "lookup": "exact person/year, positive-weight cutoff before age filter",
    },
    "engine_operations": P2_CANDIDATE_SPEC.canonical_dict(),
}
P2_REFIT_SPEC_SHA256 = v1._canonical_sha256(P2_REFIT_SPEC)


@dataclass(frozen=True)
class P2EarningsChainedRefit(EarningsChainedRefit):
    """P2-owned refit provenance with explicit removal of the second gate."""

    zero_anchor_gate_removed: bool = True
    contract_revision: str = "p2_frozen_2026_10_22"
    fit_signature: Mapping[str, Any] = field(default_factory=dict)


def refit_earnings_chained_generator_p2_v1(
    panel: pd.DataFrame,
    nawi: Mapping[int, float],
    *,
    seed: int,
    boundary_year: int = BOUNDARY_YEAR,
    qrf_factory: QRFModelFactory | None = None,
) -> P2EarningsChainedRefit:
    """Refit frozen P2 through the supplied boundary without v1 dispatch."""
    fitted = fit_forward_earnings_p2_v1(
        panel,
        nawi,
        seed=seed,
        boundary_year=boundary_year,
        qrf_factory=qrf_factory,
    )
    validate_rank_refresh_fit(fitted.generator)
    if fitted.generator.zero_anchor_gate is not None:
        raise AssertionError("P2 refit must contain exactly one shared gate")
    if fitted.n_zero_anchor_pairs != 0:
        raise AssertionError("P2 refit fitted zero-anchor pairs")
    provenance = RefitProvenance(
        boundary_year=int(boundary_year),
        estimation_rule=(
            "forward earnings income-reference period <=T*; age 25-64; "
            "nominal four-feature shared participation gate; exact prior "
            "history from positive-weight cutoff before age filtering; "
            "calendar-invariant NAWI-normalized marginal"
        ),
        n_rows={
            "estimation_panel": len(fitted.estimation_panel),
            "forward_pairs": len(fitted.forward_pairs),
            "zero_anchor_pairs": 0,
        },
        max_year={
            "earnings_reference_year": (
                None
                if fitted.estimation_panel.empty
                else int(fitted.estimation_panel["period"].max())
            )
        },
    )
    return P2EarningsChainedRefit(
        generator=fitted.generator,
        shared_gate=fitted.generator.shared_gate,
        zero_anchor_gate=None,
        estimation_panel=fitted.estimation_panel,
        forward_pairs=fitted.forward_pairs,
        anchors=fitted.anchors,
        n_zero_anchor_pairs=0,
        u_w_diagnostics=fitted.u_w_diagnostics,
        seed=int(seed),
        spec_registration=(
            "docs/design/track_b_p2_spec.md#p2_frozen_2026_10_22"
        ),
        adapter_spec_sha256=P2_REFIT_SPEC_SHA256,
        provenance=provenance,
        engine_candidate_id=P2_CANDIDATE_SPEC.candidate_id,
        engine_candidate_spec_sha256=P2_CANDIDATE_SPEC.sha256,
        q_invariant_fit_signature_sha256=(
            fitted.q_invariant_fit_signature_sha256
        ),
        rank_refresh_fit_audit=(
            None
            if fitted.rank_refresh_fit_audit is None
            else fitted.rank_refresh_fit_audit.as_dict()
        ),
        zero_anchor_gate_removed=True,
        contract_revision=P2_CANDIDATE_SPEC.contract_revision,
        fit_signature=fitted.fit_signature,
    )


def resume_p2_projection(
    generator,
    materialized_frame: pd.DataFrame,
    *,
    draw_index: int,
    completed_period: int,
    person_ordinals: Mapping[object, int],
    n_periods: int = 8,
) -> tuple[pd.DataFrame, ...]:
    """Continue materialized earnings state at its original RNG addresses.

    The caller preserves the original fitted object and complete frame; this
    adapter deliberately never invokes boundary-state initialization.
    """
    from populace_dynamics.engine.earnings_domain import wrap_earnings_domain
    from populace_dynamics.engine.loop import PeriodContext
    from populace_dynamics.engine.rng import (
        ProjectionModule,
        ProjectionRNGRegistry,
    )
    from populace_dynamics.engine.steps import advance_age, apply_earnings

    if not 0 <= completed_period <= n_periods:
        raise ValueError("invalid completed projection period")
    frame = materialized_frame.copy(deep=True)
    _require_columns(
        frame,
        ("year", *FRAME_COLUMNS, *generator.earnings_frame_update_columns),
        "P2 resume frame",
    )
    if not (frame["year"] == generator.boundary_year + completed_period).all():
        raise ValueError("P2 resume frame does not match original boundary")
    if set(frame["person_id"]) - set(person_ordinals):
        raise ValueError("P2 resume frame lacks original person ordinals")
    registry = ProjectionRNGRegistry(
        draw_index=draw_index, n_periods=n_periods
    )
    model = wrap_earnings_domain(generator)
    suffix = []
    for period_index in range(completed_period + 1, n_periods + 1):
        context = PeriodContext(
            period_index=period_index,
            year=generator.boundary_year + period_index,
            draw_index=draw_index,
            metadata={},
            rng_registry=registry,
            person_ordinals=person_ordinals,
        )
        earnings_rng = registry.generator(
            period_index, ProjectionModule.EARNINGS
        )
        frame = advance_age(frame, context, earnings_rng)
        frame = apply_earnings(frame, context, earnings_rng, model=model)
        suffix.append(frame.copy(deep=True))
    return tuple(suffix)
