"""S1's wage-relative participation gates for the candidate-3 forward law.

The nominal fitting panel and projection frame remain the v1 law's inputs.
Only a separate gate-fitting view and the two gates' query features divide
earnings by the source period's NAWI.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from typing import Any

import numpy as np
import pandas as pd

from . import forward_earnings as v1
from . import refit as v1_refit
from .candidates import (
    CANDIDATE_3,
    CandidateSpec,
    OperationSpec,
)

__all__ = [
    "CANDIDATE_S1",
    "ForwardEarningsGenerator",
    "PARTICIPATION_GATE_OPERATION_ID",
    "PARTICIPATION_GATE_OPERATION_KIND",
    "PARTICIPATION_GATE_SPEC",
    "SPEC_REGISTRATION",
    "adapter_spec_sha256",
    "fit_forward_earnings",
    "gate_fitting_view",
    "refit_earnings_chained_generator",
]

PARTICIPATION_GATE_OPERATION_KIND = "forward_earnings.participation_gate"
PARTICIPATION_GATE_OPERATION_ID = "wage_relative.v1"
CANDIDATE_S1 = CandidateSpec(
    candidate_id="m6_candidate3_engine_s1_v1",
    contract_revision="track_b_s1_frozen_2026_10_21_d1803",
    operations=(
        *CANDIDATE_3.operations,
        OperationSpec(
            kind=PARTICIPATION_GATE_OPERATION_KIND,
            implementation_id=PARTICIPATION_GATE_OPERATION_ID,
            params={},
        ),
    ),
)
SPEC_REGISTRATION = "docs/design/track_b_s1_spec.md"
PARTICIPATION_GATE_SPEC = {
    "implementation_id": PARTICIPATION_GATE_OPERATION_ID,
    "fit_earnings": "earnings / realized_nawi[period]",
    "query_earnings": "current_level / normalization_index(year - 2)",
    "target": "raw earnings_tp2",
    "weights": "raw weight_tp2",
    "form": "simple ratio; no fitted parameter",
}


def adapter_spec_sha256(base_spec_sha256: str) -> str:
    """Bind S1's gate definition to the unchanged base adapter spec."""
    return v1._canonical_sha256(
        {
            "base_adapter_spec_sha256": base_spec_sha256,
            "participation_gate": PARTICIPATION_GATE_SPEC,
        }
    )


def gate_fitting_view(
    frame: pd.DataFrame, nawi: Mapping[int, float]
) -> pd.DataFrame:
    """Copy a forward-pair frame, changing only its earnings predictor."""
    view = frame.copy(deep=True)
    source_index = np.asarray(
        [float(nawi[int(year)]) for year in frame["period"]],
        dtype=np.float64,
    )
    view["earnings"] = (
        frame["earnings"].to_numpy(dtype=np.float64) / source_index
    )
    return view


@dataclass(frozen=True)
class _GateFitResult:
    """Keep the base fitter from recording a nominal gate surface."""

    fitted: Any


@dataclass
class _GateFittingModel:
    model: v1.QRFModel
    nawi: Mapping[int, float]

    def fit(
        self,
        frame: pd.DataFrame,
        *,
        predictors: list[str],
        targets: list[str],
        weights: str,
    ) -> _GateFitResult:
        fitted = self.model.fit(
            gate_fitting_view(frame, self.nawi),
            predictors=predictors,
            targets=targets,
            weights=weights,
        )
        return _GateFitResult(fitted)


@dataclass(frozen=True)
class _GateQuery:
    fitted: Any
    wage_index: v1.ProjectedWageIndex
    year: int

    def draw_sign(
        self,
        current_level: np.ndarray,
        target_age: np.ndarray,
        uniforms: np.ndarray,
    ) -> np.ndarray:
        source_index = self.wage_index.normalization_index(int(self.year) - 2)
        return v1._gate_sign_draw(
            self.fitted, current_level / source_index, target_age, uniforms
        )


class ForwardEarningsGenerator(v1.ForwardEarningsGenerator):
    """Use S1 gate queries with all other v1 conditioning left unchanged."""

    def _gate_query_view(self, year: int) -> ForwardEarningsGenerator:
        return replace(
            self,
            shared_gate=_GateQuery(self.shared_gate, self.wage_index, year),
            zero_anchor_gate=(
                None
                if self.zero_anchor_gate is None
                else _GateQuery(self.zero_anchor_gate, self.wage_index, year)
            ),
        )

    def generate(
        self, frame: pd.DataFrame, year: int, rng: np.random.Generator
    ) -> np.ndarray:
        """Draw the v1 rank law with source-year wage-relative gate input."""
        return v1.ForwardEarningsGenerator.generate(
            self._gate_query_view(year), frame, year, rng
        )

    def generate_with_frame_updates(
        self, frame: pd.DataFrame, year: int, rng: np.random.Generator
    ) -> v1.EarningsGenerationResult:
        """Draw the correlated v1 law with the same S1 gate input."""
        return v1.ForwardEarningsGenerator.generate_with_frame_updates(
            self._gate_query_view(year), frame, year, rng
        )


def _fit_signature(fitted: v1.ForwardEarningsFit) -> str:
    generator = fitted.generator
    non_gate = v1._q_invariant_fit_signature(
        replace(generator, shared_gate=None, zero_anchor_gate=None),
        fitted.estimation_panel,
        fitted.forward_pairs,
        fitted.anchors,
        fitted.u_w_diagnostics,
    )
    gate_pairs = gate_fitting_view(
        fitted.forward_pairs, generator.wage_index.actual
    )
    return v1._canonical_sha256(
        {
            "non_gate_fit_sha256": non_gate,
            "participation_gate": PARTICIPATION_GATE_SPEC,
            "participation_gates": {
                "shared": v1._gate_fit_signature(
                    generator.shared_gate, gate_pairs
                ),
                "zero_anchor": v1._gate_fit_signature(
                    generator.zero_anchor_gate, gate_pairs
                ),
            },
        }
    )


def fit_forward_earnings(
    panel: pd.DataFrame,
    nawi: Mapping[int, float],
    *,
    seed: int,
    boundary_year: int = v1.BOUNDARY_YEAR,
    qrf_factory: v1.QRFModelFactory | None = None,
    candidate_spec: CandidateSpec | None = None,
) -> v1.ForwardEarningsFit:
    """Fit S1 from raw inputs using only separate gate-fitting views."""
    spec = CANDIDATE_S1 if candidate_spec is None else candidate_spec
    if spec.canonical_dict() != CANDIDATE_S1.canonical_dict():
        raise ValueError("S1 requires its exact frozen candidate declaration")
    factory = qrf_factory or v1._default_qrf_factory

    def gate_factory(*, seed: int) -> _GateFittingModel:
        return _GateFittingModel(factory(seed=seed), nawi)

    fitted = v1.fit_forward_earnings(
        panel,
        nawi,
        seed=seed,
        boundary_year=boundary_year,
        qrf_factory=gate_factory,
        candidate_spec=spec,
    )
    base = fitted.generator
    values = {field.name: getattr(base, field.name) for field in fields(base)}
    values["shared_gate"] = base.shared_gate.fitted
    values["zero_anchor_gate"] = (
        None if base.zero_anchor_gate is None else base.zero_anchor_gate.fitted
    )
    fitted = replace(fitted, generator=ForwardEarningsGenerator(**values))
    return replace(
        fitted, q_invariant_fit_signature_sha256=_fit_signature(fitted)
    )


def refit_earnings_chained_generator(
    panel: pd.DataFrame,
    nawi: Mapping[int, float],
    *,
    seed: int,
    boundary_year: int = v1_refit.BOUNDARY_YEAR,
    qrf_factory: v1.QRFModelFactory | None = None,
    candidate_spec: CandidateSpec | None = None,
) -> v1_refit.EarningsChainedRefit:
    """Refit S1 with v1's support and provenance, and S1's own identity.

    The result construction mirrors the protected v1 refit entry point.
    Keeping the fitting call here leaves that entry point and the registered
    candidate-3 path unchanged.
    """
    spec = CANDIDATE_S1 if candidate_spec is None else candidate_spec
    fitted = fit_forward_earnings(
        panel,
        nawi,
        seed=seed,
        boundary_year=boundary_year,
        qrf_factory=qrf_factory or v1_refit._default_qrf_factory,
        candidate_spec=spec,
    )
    v1.validate_rank_refresh_fit(fitted.generator)
    provenance = v1_refit.RefitProvenance(
        boundary_year=boundary_year,
        estimation_rule=(
            "forward earnings income-reference period <=T*; age 25-64; "
            "calendar-invariant NAWI-normalized marginal"
        ),
        n_rows={
            "estimation_panel": len(fitted.estimation_panel),
            "forward_pairs": len(fitted.forward_pairs),
            "zero_anchor_pairs": fitted.n_zero_anchor_pairs,
        },
        max_year={
            "earnings_reference_year": v1_refit._max_year(
                fitted.estimation_panel, "period"
            )
        },
    )
    return v1_refit.EarningsChainedRefit(
        generator=fitted.generator,
        shared_gate=fitted.generator.shared_gate,
        zero_anchor_gate=fitted.generator.zero_anchor_gate,
        estimation_panel=fitted.estimation_panel,
        forward_pairs=fitted.forward_pairs,
        anchors=fitted.anchors,
        n_zero_anchor_pairs=fitted.n_zero_anchor_pairs,
        u_w_diagnostics=fitted.u_w_diagnostics,
        seed=int(seed),
        spec_registration=SPEC_REGISTRATION,
        adapter_spec_sha256=adapter_spec_sha256(v1_refit.EARNINGS_SPEC_SHA256),
        provenance=provenance,
        engine_candidate_id=spec.candidate_id,
        engine_candidate_spec_sha256=spec.sha256,
        q_invariant_fit_signature_sha256=(
            fitted.q_invariant_fit_signature_sha256
        ),
        rank_refresh_fit_audit=(
            None
            if fitted.rank_refresh_fit_audit is None
            else fitted.rank_refresh_fit_audit.as_dict()
        ),
    )
