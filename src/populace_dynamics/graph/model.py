"""Validated JSON for the existing fitted M6 mortality law; no pickle."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

_FORMAT = "populace-dynamics.mortality"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def read_json(path):
    """Read JSON without accepting duplicate fields or nonfinite numbers."""
    return parse_json(path.read_bytes())


def parse_json(payload):
    def invalid(value):
        raise ValueError(f"nonfinite JSON number {value}")

    try:
        return json.loads(
            payload, object_pairs_hook=_unique_object, parse_constant=invalid
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid mortality JSON") from error


def json_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _integer(value, label):
    if type(value) is not int:
        raise ValueError(f"{label} must be an integer")
    return value


@dataclass(frozen=True)
class MortalityArtifact:
    """A compact model with an explicit fit boundary and source vintage."""

    bands: tuple[tuple[int, int], ...]
    probabilities: tuple[tuple[str, str, float], ...]
    boundary_year: int
    external_vintage_year: int
    fit_rows: int

    def __post_init__(self):
        _integer(self.boundary_year, "boundary_year")
        _integer(self.external_vintage_year, "external_vintage_year")
        if _integer(self.fit_rows, "fit_rows") <= 0:
            raise ValueError("fit_rows must be positive")
        if self.external_vintage_year > self.boundary_year:
            raise ValueError("external vintage is later than the fit boundary")
        seen = set()
        for label, sex, probability in self.probabilities:
            if not isinstance(label, str) or sex not in ("female", "male"):
                raise ValueError("invalid mortality probability cell")
            if (label, sex) in seen:
                raise ValueError("duplicate mortality probability cell")
            seen.add((label, sex))
            if isinstance(probability, bool) or not isinstance(
                probability, (int, float)
            ):
                raise ValueError("mortality probability must be numeric")
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError("mortality probability must lie in [0, 1]")
        for band in self.bands:
            if len(band) != 2 or any(type(age) is not int for age in band):
                raise ValueError("mortality bands must contain integer bounds")
        # The real model validates complete, contiguous bands and sex cells.
        _ = self.model

    @property
    def model(self):
        from populace_dynamics.engine.steps import AgeSexMortalityModel

        return AgeSexMortalityModel(
            self.bands,
            {(band, sex): p for band, sex, p in self.probabilities},
        )

    def to_bytes(self):
        return json_bytes(
            {
                "format": _FORMAT,
                "schema_version": 1,
                "boundary_year": self.boundary_year,
                "external_vintage_year": self.external_vintage_year,
                "fit_rows": self.fit_rows,
                "bands": self.bands,
                "probabilities": [
                    {"age_band": band, "sex": sex, "probability": p}
                    for band, sex, p in sorted(self.probabilities)
                ],
            }
        )

    @classmethod
    def from_bytes(cls, payload):
        raw = parse_json(payload)
        expected = {
            "format",
            "schema_version",
            "boundary_year",
            "external_vintage_year",
            "fit_rows",
            "bands",
            "probabilities",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise ValueError("mortality model has an invalid field set")
        if raw["format"] != _FORMAT or type(raw["schema_version"]) is not int:
            raise ValueError("invalid mortality format or schema version")
        if raw["schema_version"] != 1:
            raise ValueError("unsupported mortality schema version")
        if not isinstance(raw["bands"], list) or not all(
            isinstance(band, list) for band in raw["bands"]
        ):
            raise ValueError("mortality bands must be arrays")
        if not isinstance(raw["probabilities"], list):
            raise ValueError("mortality probabilities must be an array")
        for row in raw["probabilities"]:
            if not isinstance(row, dict) or set(row) != {
                "age_band",
                "sex",
                "probability",
            }:
                raise ValueError("invalid mortality probability fields")
        return cls(
            bands=tuple(tuple(band) for band in raw["bands"]),
            probabilities=tuple(
                (row["age_band"], row["sex"], row["probability"])
                for row in raw["probabilities"]
            ),
            boundary_year=raw["boundary_year"],
            external_vintage_year=raw["external_vintage_year"],
            fit_rows=raw["fit_rows"],
        )


def fit_mortality(
    exposure, external_rates, *, boundary_year, external_vintage_year
):
    """Use the existing cutoff-safe fitter and retain its compact results."""
    from populace_dynamics.engine.refit import (
        fit_mortality_model,
        prepare_mortality_refit_inputs,
    )

    prepared = prepare_mortality_refit_inputs(
        exposure,
        external_rates,
        boundary_year=boundary_year,
        external_vintage_year=external_vintage_year,
    )
    model = fit_mortality_model(prepared)
    return MortalityArtifact(
        bands=model.bands,
        probabilities=tuple(
            (band, sex, p)
            for (band, sex), p in sorted(model.probability.items())
        ),
        boundary_year=boundary_year,
        external_vintage_year=external_vintage_year,
        fit_rows=len(prepared.exposure),
    )
