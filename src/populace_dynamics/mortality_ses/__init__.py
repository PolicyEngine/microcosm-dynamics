"""Opt-in differential mortality; no fitted gradients or projection wiring."""

from .model import DifferentialMortality
from .normalizer import CELL_LOG_COLUMNS, normalize_probabilities
from .specification import (
    CoefficientPath,
    HoldLastCoefficientPath,
    RelativeRiskSpec,
    RiskDimension,
    UnclassifiedValueError,
)
from .step import apply_differential_mortality

__all__ = [
    "CELL_LOG_COLUMNS",
    "CoefficientPath",
    "DifferentialMortality",
    "HoldLastCoefficientPath",
    "RelativeRiskSpec",
    "RiskDimension",
    "UnclassifiedValueError",
    "apply_differential_mortality",
    "normalize_probabilities",
]
