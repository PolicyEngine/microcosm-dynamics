"""Pure, year-aware differential mortality around a single-age baseline."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import ClassVar, Protocol

import numpy as np
import pandas as pd

from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    SINGLE_YEAR_AGE_BANDS,
    DIEntitlementRates,
    DIEntitlementSpec,
)
from populace_dynamics.engine.loop import PeriodContext

from .normalizer import normalize_probabilities
from .specification import RelativeRiskSpec, UnclassifiedValueError


class YearAwareMortality(Protocol):
    """The context-aware baseline protocol; no yearless probability API."""

    bands: tuple[tuple[int, int], ...]

    def __call__(
        self, frame: pd.DataFrame, context: PeriodContext
    ) -> np.ndarray: ...


def _integer_values(series: pd.Series, column: str) -> np.ndarray:
    """Refuse missing, fractional and non-finite integer inputs."""
    try:
        values = series.to_numpy(dtype=np.float64, na_value=np.nan)
    except (TypeError, ValueError) as error:
        raise ValueError(f"column {column!r} must contain integers") from error
    if (
        not np.isfinite(values).all()
        or (values != np.floor(values)).any()
        or (values < np.iinfo(np.int64).min).any()
        or (values >= float(np.iinfo(np.int64).max)).any()
    ):
        raise ValueError(f"column {column!r} must contain finite integers")
    return values.astype(np.int64)


def _weights(frame: pd.DataFrame, column: str | None) -> np.ndarray:
    if column is None:
        return np.ones(len(frame), dtype=np.float64)
    if column not in frame:
        raise ValueError(
            f"mortality frame is missing weight column {column!r}"
        )
    try:
        values = frame[column].to_numpy(dtype=np.float64, na_value=np.nan)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "mortality weights must be finite and >= 0"
        ) from error
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("mortality weights must be finite and >= 0")
    return values


@dataclass(frozen=True)
class DifferentialMortality:
    """Redistribute baseline deaths within single age, sex and year cells.

    ``weight_column`` is required explicitly; ``None`` counts persons equally.
    If birth year is present, uncapped age must equal ``year - 1 - birth_year``
    regardless of the DI adapter's optional age validation. Both this model
    and the adapter then cap cell ages at 120. DI-origin rows retain baseline
    q so the adapter, using the same DI configuration, owns their death rates.

    This model deliberately exposes no ``probabilities`` attribute: the DI
    adapter dispatches that attribute without a context or a projection year.
    ``evaluate`` additionally returns the pure normalizer's cell accounting.
    The adapter keeps only probabilities, so ``cell_log``, when given,
    receives each ``__call__``'s cell accounting keyed by projection year.
    """

    baseline: YearAwareMortality
    specification: RelativeRiskSpec
    weight_column: str | None = field(kw_only=True)
    di_configuration: DIEntitlementRates | DIEntitlementSpec | None = field(
        default=None, kw_only=True
    )
    cell_log: MutableMapping[int, pd.DataFrame] | None = field(
        default=None, kw_only=True, compare=False, repr=False
    )
    bands: ClassVar[tuple[tuple[int, int], ...]] = SINGLE_YEAR_AGE_BANDS

    def __post_init__(self) -> None:
        if hasattr(self, "probabilities"):
            raise ValueError(
                "DifferentialMortality must not expose a probabilities "
                "attribute; its interface requires context"
            )
        if hasattr(self.baseline, "probabilities"):
            raise ValueError(
                "baseline must use (frame, context), without a probabilities "
                "attribute"
            )
        if not callable(self.baseline):
            raise TypeError("baseline must be callable as (frame, context)")
        if tuple(getattr(self.baseline, "bands", ())) != self.bands:
            raise ValueError("baseline bands must be SINGLE_YEAR_AGE_BANDS")
        if self.weight_column is not None and not isinstance(
            self.weight_column, str
        ):
            raise TypeError("weight_column must be a column name or None")
        if self.di_configuration is not None and not isinstance(
            self.di_configuration, (DIEntitlementRates, DIEntitlementSpec)
        ):
            raise TypeError("di_configuration must be DI rates or their spec")
        if self.cell_log is not None and not isinstance(
            self.cell_log, MutableMapping
        ):
            raise TypeError("cell_log must be a mutable mapping or None")

    def _fixed_rows(self, frame: pd.DataFrame) -> np.ndarray:
        columns = {"di_entitled", "di_conversion_year"}
        present = {
            column
            for column in frame.columns
            if isinstance(column, str) and column.startswith("di_")
        }
        if self.di_configuration is None:
            if present:
                raise ValueError(
                    "DI columns require di_configuration matching the adapter"
                )
            return np.zeros(len(frame), dtype=bool)
        missing = columns.difference(frame.columns)
        if missing:
            raise ValueError(
                f"mortality frame is missing columns {sorted(missing)}"
            )
        entitled = frame["di_entitled"]
        if entitled.isna().any():
            raise ValueError("column 'di_entitled' has missing values")
        if not (
            pd.api.types.is_bool_dtype(entitled.dtype)
            or entitled.isin([True, False]).all()
        ):
            raise ValueError("column 'di_entitled' must be boolean")
        conversion = frame["di_conversion_year"]
        converted = conversion.notna().to_numpy(dtype=bool)
        _integer_values(conversion.loc[converted], "di_conversion_year")
        spec = (
            self.di_configuration.spec
            if isinstance(self.di_configuration, DIEntitlementRates)
            else self.di_configuration
        )
        return entitled.to_numpy(dtype=bool) | (
            converted & (spec.post_conversion_mortality == "di_origin")
        )

    def evaluate(
        self, frame: pd.DataFrame, context: PeriodContext
    ) -> tuple[np.ndarray, pd.DataFrame]:
        """Return probabilities and cell accounting without consuming RNG."""
        missing = {"age", "sex"}.difference(frame.columns)
        if missing:
            raise ValueError(
                f"mortality frame is missing columns {sorted(missing)}"
            )
        year = int(context.year)
        if year != context.year:
            raise ValueError("mortality context year must be an integer")
        age = _integer_values(frame["age"], "age")
        if (age < 0).any():
            raise ValueError("mortality ages must be non-negative")
        if "birth_year" in frame:
            birth_year = _integer_values(frame["birth_year"], "birth_year")
            if (age != year - 1 - birth_year).any():
                raise ValueError(
                    "mortality age must equal context.year - 1 - birth_year "
                    "before capping at 120"
                )
        ages = np.minimum(age, MAX_AGE)
        sex = frame["sex"].astype(str).to_numpy()
        if not np.isin(sex, ("female", "male")).all():
            raise ValueError("mortality sex must be 'female' or 'male'")
        weights = _weights(frame, self.weight_column)
        fixed = self._fixed_rows(frame)
        baseline = np.asarray(self.baseline(frame, context), dtype=np.float64)
        if baseline.shape != (len(frame),):
            raise ValueError("baseline mortality returned the wrong shape")
        if (
            not np.isfinite(baseline).all()
            or ((baseline < 0) | (baseline > 1)).any()
        ):
            raise ValueError("baseline mortality must lie in [0, 1]")
        cells = list(zip([year] * len(frame), sex, ages, strict=True))
        try:
            risk, unclassified = self.specification.relative_risks(
                frame, year, ages
            )
        except UnclassifiedValueError as error:
            _, error.cell_log = normalize_probabilities(
                baseline,
                np.ones(len(frame)),
                fixed,
                baseline,
                cells,
                weights,
                unclassified_counts=error.unclassified_counts,
            )
            raise
        return normalize_probabilities(
            baseline,
            risk,
            fixed,
            baseline,
            cells,
            weights,
            unclassified_counts=unclassified,
        )

    def __call__(
        self, frame: pd.DataFrame, context: PeriodContext
    ) -> np.ndarray:
        probabilities, cells = self.evaluate(frame, context)
        if self.cell_log is not None:
            self.cell_log[int(context.year)] = cells
        return probabilities
