"""R1: pinned retirement earnings test (RET) parameters, without a ledger.

Verification class: statutory conformance plus historical-source checks.
The bundled table admits parameter values only for its listed years.
Projections are conditional on an explicitly permitted input vintage; they
admit no population, behavioral, or forecast-validation claim.

Authority: Social Security Act section 203(f)(3), (8)(A)-(E),
https://www.ssa.gov/OP_Home/ssact/title02/0203.htm, and SSA's method,
https://www.ssa.gov/oact/cola/rtdet.html. Captured bytes and hashes are in
tests/data/track_b/ret_sources/. The current formula uses monthly bases
$670 (1994) / NAWI(1992) and $2,500 (2002) / NAWI(2000). Rounding monthly
amounts to $10, with $5 ties upward, is equivalent to rounding annual
amounts to $120, with $60 ties upward. Only a positive COLA effective in
December of year y-1 permits indexing for y. NAWI is from year y-2.

The historical 2000 and 2001 higher limits are legislative amounts, not
outputs of the post-2002 formula. This module assumes unchanged law for
projections: section 203(f)(8)(C)'s new-legislation override requires a new
parameter version. It does not implement payment timing or deductions.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from importlib.resources import files
from types import MappingProxyType
from typing import Literal

import yaml

ExactNumber = int | str | Decimal | Fraction
Status = Literal["realized", "projected"]

# SSA's pinned base values; annual dollars / annual wage-index dollars.
_BASES = {
    "lower": (8040, Fraction("22935.42")),
    "higher": (30000, Fraction("32154.82")),
}


def _exact(value: ExactNumber) -> Fraction:
    if isinstance(value, bool) or not isinstance(
        value, (int, str, Decimal, Fraction)
    ):
        raise TypeError(
            "Use an exact int, decimal string, Decimal or Fraction"
        )
    return Fraction(value)


def _year(year: int) -> None:
    if type(year) is not int or year < 1:
        raise ValueError("Year must be a positive integer")


@dataclass(frozen=True)
class SourcePin:
    """Identity of captured source bytes, including their UTC retrieval time."""

    url: str
    retrieved_at: str
    sha256: str

    def __post_init__(self):
        if not self.url.startswith("https://"):
            raise ValueError("Source URL must be HTTPS")
        when = datetime.fromisoformat(self.retrieved_at.replace("Z", "+00:00"))
        if when.utcoffset() is None or when.utcoffset().total_seconds() != 0:
            raise ValueError("Source retrieval time must include UTC timezone")
        if len(self.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.sha256
        ):
            raise ValueError("Source SHA-256 must be 64 lowercase hex digits")


@dataclass(frozen=True)
class ParameterValue:
    """Exact value with publication status and all source identities.

    For a projection, sources include its prior amount and its NAWI/COLA
    inputs. A projected value is never relabelled as published by SSA.
    """

    value: ExactNumber
    status: Status
    sources: tuple[SourcePin, ...]

    def __post_init__(self):
        value = _exact(self.value)
        if value < 0:
            raise ValueError("Parameter value must be nonnegative")
        if self.status not in ("realized", "projected"):
            raise ValueError("Status must be realized or projected")
        sources = tuple(self.sources)
        if not sources or any(not isinstance(s, SourcePin) for s in sources):
            raise ValueError("Every value needs at least one pinned source")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "sources", sources)


@dataclass(frozen=True)
class RETYear:
    """Annual exempt amounts and exact excess-earnings withholding rates.

    The higher amount/rate applies in the FRA-attainment year, counting
    earnings before the FRA month only. From the FRA month, RET ceases.
    Amounts here are annual limits, not monthly payment instructions.
    """

    year: int
    lower_exempt_amount: ParameterValue
    higher_exempt_amount: ParameterValue
    lower_withholding_rate: ParameterValue
    higher_withholding_rate: ParameterValue
    vintage: str | None = None
    vintage_sha256: str | None = None

    def __post_init__(self):
        _year(self.year)
        for amount in (self.lower_exempt_amount, self.higher_exempt_amount):
            if amount.value <= 0 or amount.value.denominator != 1:
                raise ValueError(
                    "Annual exempt amounts must be positive dollars"
                )
        if self.lower_withholding_rate.value != Fraction(1, 2):
            raise ValueError("The lower withholding rate must be exactly 1/2")
        if self.higher_withholding_rate.value != Fraction(1, 3):
            raise ValueError("The higher withholding rate must be exactly 1/3")
        if (
            any(
                amount.status == "projected"
                for amount in (
                    self.lower_exempt_amount,
                    self.higher_exempt_amount,
                )
            )
            and not self.vintage
        ):
            raise ValueError("Projected amounts require a named input vintage")


@dataclass(frozen=True)
class ProjectionInputs:
    """An explicitly supplied, frozen vintage, separate from SSA history.

    NAWI keys denote wage years; COLA keys denote December effective years
    and values are percentages. The caller registers this vintage's source
    hashes before any empirical run. There is no default wage forecast and
    no lookup into the historical test fixtures to fill gaps.
    """

    vintage: str
    nawi: Mapping[int, ParameterValue]
    december_cola_percent: Mapping[int, ParameterValue]

    def __post_init__(self):
        if not isinstance(self.vintage, str) or not self.vintage.strip():
            raise ValueError("A nonempty input vintage is required")
        for name in ("nawi", "december_cola_percent"):
            values = dict(getattr(self, name))
            for year, value in values.items():
                _year(year)
                if not isinstance(value, ParameterValue):
                    raise TypeError(
                        "Vintage inputs must be sourced parameter values"
                    )
                if name == "nawi" and value.value <= 0:
                    raise ValueError("NAWI must be positive")
            object.__setattr__(self, name, MappingProxyType(values))

    @property
    def fingerprint(self) -> str:
        """Bind the entire vintage's exact values, statuses and source pins."""
        payload = {"vintage": self.vintage}
        for name in ("nawi", "december_cola_percent"):
            payload[name] = [
                {
                    "year": year,
                    "value": str(value.value),
                    "status": value.status,
                    "sources": [
                        (pin.url, pin.retrieved_at, pin.sha256)
                        for pin in value.sources
                    ],
                }
                for year, value in sorted(getattr(self, name).items())
            ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode()).hexdigest()


def project_exempt_amount(
    *,
    kind: Literal["lower", "higher"],
    nawi: ExactNumber,
    prior_amount: int,
    preceding_december_cola: ExactNumber,
) -> int:
    """Apply the current statutory formula using exact rational arithmetic.

    This is a scalar rule primitive. Use ``project_ret_year`` for dated,
    provenance-carrying projections with vintage and missing-year checks.
    ``prior_amount`` must be a valid annual formula-era amount (a multiple
    of $120); the 2000/2001 higher legislative overrides are out of scope.
    """
    if kind not in _BASES:
        raise ValueError("Exempt amount kind must be lower or higher")
    wage = _exact(nawi)
    cola = _exact(preceding_december_cola)
    if wage <= 0 or cola < 0:
        raise ValueError("NAWI must be positive and COLA nonnegative")
    if (
        type(prior_amount) is not int
        or prior_amount <= 0
        or prior_amount % 120
    ):
        raise ValueError("Prior amount must be a positive multiple of $120")
    if not cola:
        return prior_amount
    base, base_wage = _BASES[kind]
    units = base * wage / base_wage / 120
    # floor(units + 1/2): exact halfway cases round upward, never to even.
    rounded = 120 * (
        (units.numerator * 2 + units.denominator) // (2 * units.denominator)
    )
    return max(prior_amount, rounded)


def project_ret_year(
    prior: RETYear,
    inputs: ProjectionInputs,
    *,
    permitted_vintage: str,
) -> RETYear:
    """Project one consecutive year from only the permitted vintage.

    Missing inputs raise even when COLA is zero: a complete, explicit
    vintage is required, and no historical value is silently substituted.
    Projected chains must retain the same vintage throughout.
    """
    if inputs.vintage != permitted_vintage:
        raise ValueError("Input vintage does not match the permitted vintage")
    if prior.vintage is not None and prior.vintage != permitted_vintage:
        raise ValueError(
            "Prior projected amount belongs to a different vintage"
        )
    if (
        prior.vintage is not None
        and prior.vintage_sha256 != inputs.fingerprint
    ):
        raise ValueError(
            "Prior projected amount uses a different vintage payload"
        )
    year = prior.year + 1
    if year < 2003:
        raise ValueError("The current projection formula supports 2003 onward")
    wage = inputs.nawi[year - 2]
    cola = inputs.december_cola_percent[year - 1]

    def amount(kind: Literal["lower", "higher"]) -> ParameterValue:
        previous = getattr(prior, f"{kind}_exempt_amount")
        value = project_exempt_amount(
            kind=kind,
            nawi=wage.value,
            prior_amount=int(previous.value),
            preceding_december_cola=cola.value,
        )
        sources = tuple(
            dict.fromkeys(previous.sources + wage.sources + cola.sources)
        )
        return ParameterValue(value, "projected", sources)

    return RETYear(
        year,
        amount("lower"),
        amount("higher"),
        prior.lower_withholding_rate,
        prior.higher_withholding_rate,
        inputs.vintage,
        inputs.fingerprint,
    )


@dataclass(frozen=True)
class RETParameters:
    """An immutable, explicitly enumerated parameter table; no carry-forward."""

    years: Mapping[int, RETYear]
    parameter_sha256: str

    def __post_init__(self):
        values = dict(self.years)
        if not values:
            raise ValueError("A RET parameter table cannot be empty")
        for year, value in values.items():
            _year(year)
            if year != value.year:
                raise ValueError("Parameter table key does not match its year")
        object.__setattr__(self, "years", MappingProxyType(values))

    def for_year(self, year: int) -> RETYear:
        _year(year)
        try:
            return self.years[year]
        except KeyError:
            raise KeyError(
                f"RET parameters unavailable for year {year}"
            ) from None

    def project_through(
        self,
        end_year: int,
        inputs: ProjectionInputs,
        *,
        permitted_vintage: str,
    ) -> "RETParameters":
        """Append explicit projections, leaving published values untouched."""
        _year(end_year)
        if inputs.vintage != permitted_vintage:
            raise ValueError(
                "Input vintage does not match the permitted vintage"
            )
        last = max(self.years)
        if end_year < last:
            raise ValueError("Projection end precedes the table's last year")
        values = dict(self.years)
        for year in range(last + 1, end_year + 1):
            values[year] = project_ret_year(
                values[year - 1], inputs, permitted_vintage=permitted_vintage
            )
        return RETParameters(values, self.parameter_sha256)


def load_ret_parameters() -> RETParameters:
    """Load the bundled v1 table and resolve source pins for every value.

    The YAML hash identifies the published baseline, including its pins.
    Forecast input hashes remain on each projected value's source records.
    """
    raw = (
        files("populace_dynamics.track_b.parameters")
        .joinpath("ret_v1.yaml")
        .read_bytes()
    )
    document = yaml.safe_load(raw)
    if document["schema_version"] != 1:
        raise ValueError("Unsupported RET parameter schema")
    pins = {
        key: SourcePin(**value) for key, value in document["sources"].items()
    }

    def parameter(record):
        return ParameterValue(
            record["value"],
            record["status"],
            tuple(pins[key] for key in record["sources"]),
        )

    rates = {key: parameter(value) for key, value in document["rates"].items()}
    years = {
        year: RETYear(
            year,
            parameter(record["lower_exempt_amount"]),
            parameter(record["higher_exempt_amount"]),
            rates["lower_withholding_rate"],
            rates["higher_withholding_rate"],
        )
        for year, record in document["years"].items()
    }
    return RETParameters(years, sha256(raw).hexdigest())
