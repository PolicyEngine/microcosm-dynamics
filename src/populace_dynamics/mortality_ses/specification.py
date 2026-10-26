"""Explicit, year-indexed log-additive mortality relative risks.

No empirical coefficients or category definitions are supplied here. SM2 owns
those inputs; the mechanism requires all three named dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd

DIMENSIONS = ("lifetime_earnings", "education", "race_hispanic_origin")
SEXES = ("female", "male")
MAX_AGE = 120
KEYS = ["dimension", "category", "sex", "age"]
LOG_RISK = "log_relative_risk"


class UnclassifiedValueError(ValueError):
    """A refusal carrying row counts; model evaluation adds its cell log."""

    def __init__(self, counts: dict[str, np.ndarray]):
        self.unclassified_counts = counts
        self.cell_log: pd.DataFrame | None = None
        super().__init__(
            "unclassified mortality attributes under refuse: "
            f"{int(counts['unclassified_refuse'].sum())} contributions"
        )


@dataclass(frozen=True)
class RiskDimension:
    """Ordered categories and a zero-log-risk reference for one dimension."""

    name: str
    column: str
    categories: tuple[str, ...]
    reference: str
    unclassified_values: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "categories", tuple(self.categories))
        object.__setattr__(
            self, "unclassified_values", tuple(self.unclassified_values)
        )
        if self.name not in DIMENSIONS or not self.column:
            raise ValueError("dimension needs a known name and frame column")
        if (
            not self.categories
            or any(not isinstance(c, str) or not c for c in self.categories)
            or len(set(self.categories)) != len(self.categories)
            or self.reference not in self.categories
        ):
            raise ValueError("categories must be unique with a reference")
        if set(self.categories) & set(self.unclassified_values):
            raise ValueError("unclassified values overlap categories")


class CoefficientPath(Protocol):
    """SM2 extension point: complete coefficient tables for named years.

    ``coefficients`` returns dimension/category/sex/age/log_relative_risk
    rows (or inclusive age_lower/age_upper bands). Every table is validated,
    including a custom path's output at evaluation time.
    """

    @property
    def years(self) -> tuple[int, ...]: ...

    def coefficients(self, year: int) -> pd.DataFrame: ...


class HoldLastCoefficientPath:
    """A step-held table; after its last year the final gradient persists."""

    def __init__(self, table: pd.DataFrame):
        if "year" not in table or table.empty:
            raise ValueError("coefficient table needs nonempty year coverage")
        years = table["year"].to_numpy(dtype=float)
        if (
            not np.isfinite(years).all()
            or (years != np.floor(years)).any()
            or (years < np.iinfo(np.int64).min).any()
            or (years >= float(np.iinfo(np.int64).max)).any()
        ):
            raise ValueError("coefficient years must be finite integers")
        self._table = table.copy(deep=True)
        self._table["year"] = years.astype(int)
        self._years = tuple(sorted(set(years.astype(int))))

    @property
    def years(self) -> tuple[int, ...]:
        return self._years

    def coefficients(self, year: int) -> pd.DataFrame:
        if year < self.years[0]:
            raise ValueError("year precedes first mortality coefficient year")
        selected = max(y for y in self.years if y <= year)
        return (
            self._table.loc[self._table["year"] == selected]
            .drop(columns="year")
            .copy(deep=True)
        )


def _expanded(table: pd.DataFrame) -> pd.DataFrame:
    missing = set(KEYS[:-1] + [LOG_RISK]) - set(table.columns)
    if missing:
        raise ValueError(
            f"coefficient table missing columns {sorted(missing)}"
        )
    if "age" in table:
        out = table.copy(deep=True)
    elif {"age_lower", "age_upper"} <= set(table.columns):
        rows = []
        for row in table.to_dict("records"):
            lower, upper = row.pop("age_lower"), row.pop("age_upper")
            if (
                not np.isfinite([lower, upper]).all()
                or int(lower) != lower
                or int(upper) != upper
                or not 0 <= lower <= upper <= MAX_AGE
            ):
                raise ValueError("invalid inclusive coefficient age band")
            rows.extend(
                dict(row, age=age) for age in range(int(lower), int(upper) + 1)
            )
        out = pd.DataFrame(rows, columns=[*KEYS, LOG_RISK])
    else:
        raise ValueError("coefficient table needs age or inclusive age bands")
    age = out["age"].to_numpy(dtype=float)
    if (
        not np.isfinite(age).all()
        or (age != np.floor(age)).any()
        or ((age < 0) | (age > MAX_AGE)).any()
    ):
        raise ValueError("coefficient ages must be integers 0-120")
    out["age"] = age.astype(int)
    return out


@dataclass(frozen=True)
class RelativeRiskSpec:
    """Validated joint specification, with explicit unclassified handling."""

    dimensions: tuple[RiskDimension, ...]
    path: CoefficientPath
    unclassified_rule: str = "refuse"

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimensions", tuple(self.dimensions))
        if len(self.dimensions) != len(DIMENSIONS) or {
            d.name for d in self.dimensions
        } != set(DIMENSIONS):
            raise ValueError("specification must cover all three dimensions")
        if len({d.column for d in self.dimensions}) != len(DIMENSIONS):
            raise ValueError("each dimension needs its own frame column")
        if self.unclassified_rule not in ("refuse", "reference"):
            raise ValueError("unclassified rule must be refuse or reference")
        years = tuple(self.path.years)
        if not years or tuple(sorted(set(years))) != years:
            raise ValueError("path years must be nonempty, unique and ordered")
        if any(not isinstance(y, (int, np.integer)) for y in years):
            raise ValueError("path years must be integers")
        for year in years:
            self._validated_table(year)

    def _validated_table(self, year: int) -> pd.Series:
        if year < self.path.years[0]:
            raise ValueError("year precedes first mortality coefficient year")
        table = _expanded(self.path.coefficients(year))
        if table[KEYS].isna().any().any() or table.duplicated(KEYS).any():
            raise ValueError("coefficient keys missing or duplicated")
        expected = {
            (dimension.name, category, sex, age)
            for dimension in self.dimensions
            for category in dimension.categories
            for sex in SEXES
            for age in range(MAX_AGE + 1)
        }
        if set(table[KEYS].itertuples(index=False, name=None)) != expected:
            raise ValueError("coefficient coverage or categories do not match")
        values = table[LOG_RISK].to_numpy(dtype=float)
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            risks = np.exp(values)
        if not np.isfinite(risks).all() or (risks <= 0).any():
            raise ValueError("every relative risk must be finite and positive")
        for dimension in self.dimensions:
            reference = (table["dimension"] == dimension.name) & (
                table["category"] == dimension.reference
            )
            if (values[reference] != 0).any():
                raise ValueError("reference category must have zero log risk")
        return table.set_index(KEYS)[LOG_RISK]

    def relative_risks(
        self, frame: pd.DataFrame, year: int, ages: np.ndarray
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """Return log-additive risks and explicit per-dimension row counts."""
        required = {d.column for d in self.dimensions} | {"sex"}
        if required - set(frame.columns):
            raise ValueError(
                "mortality frame missing dimension or sex columns"
            )
        sex = frame["sex"].to_numpy()
        if not frame["sex"].isin(SEXES).all():
            raise ValueError("unknown mortality sex")
        ages = np.asarray(ages)
        if (
            ages.shape != (len(frame),)
            or not np.isin(ages, np.arange(MAX_AGE + 1)).all()
        ):
            raise ValueError("risk ages must be single ages 0-120")
        coefficients = self._validated_table(year)
        total = np.zeros(len(frame))
        counts = {
            "unclassified_refuse": np.zeros(len(frame), dtype=int),
            "unclassified_reference": np.zeros(len(frame), dtype=int),
        }
        for dimension in self.dimensions:
            values = frame[dimension.column]
            unclassified = (
                values.isna() | values.isin(dimension.unclassified_values)
            ).to_numpy()
            if (
                ~(values.isin(dimension.categories).to_numpy() | unclassified)
            ).any():
                raise ValueError(f"unknown category in {dimension.name}")
            key = f"unclassified_{self.unclassified_rule}"
            counts[key] += unclassified
            for rule in ("refuse", "reference"):
                counts[f"{dimension.name}_unclassified_{rule}"] = (
                    unclassified.astype(int)
                    if rule == self.unclassified_rule
                    else np.zeros(len(frame), dtype=int)
                )
            categories = values.where(~unclassified, dimension.reference)
            index = pd.MultiIndex.from_arrays(
                [[dimension.name] * len(frame), categories, sex, ages],
                names=KEYS,
            )
            total += coefficients.reindex(index).to_numpy(dtype=float)
        if counts["unclassified_refuse"].any():
            raise UnclassifiedValueError(counts)
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            risks = np.exp(total)
        if not np.isfinite(risks).all() or (risks <= 0).any():
            raise ValueError(
                "combined relative risks must be finite and positive"
            )
        return risks, counts
