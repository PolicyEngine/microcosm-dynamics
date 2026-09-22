"""Run retained earnings histories through the actual Axiom AIME/PIA engine.

The bridge transports facts; it does not calculate benefits.  It builds
``axiom-rules-engine/lifetime-request/v2`` requests in the format of the
retained SSA Case A runner, executes the real ``run-lifetime`` binary as a
subprocess against pinned compiled artifacts, and parses the typed response.
Wage indexing, computation-year selection, averaging and the ordinary PIA
formula all happen inside the engine.

The bound RuleSpec modules are unaccepted encoder candidates.  Numerical
agreement with a published example is diagnostic only.  When a person lacks
an input the candidates need, the bridge raises
:class:`BenefitBridgeRefusal` instead of guessing.  It never pads missing
years with zeros, never treats projected labor income as creditable
earnings without an explicit caller declaration, and requests the PIA output
only for the candidate's supplied 2026 first-eligibility cohort.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from numbers import Integral
from pathlib import Path

from .closed_cohort_history import ClosedCohortEarningsHistory

AIME_OUTPUT = "us:statutes/42/415/b#average_indexed_monthly_earnings"
PIA_OUTPUT = "us:statutes/42/415/a#ordinary_pia_before_cola"
AIME_INPUT_PREFIX = "us:statutes/42/415/b#input."
PIA_COHORT_INPUT = (
    "us:statutes/42/415/a#input.supplied_2026_first_eligibility_cohort"
)
# The 415(a) candidate gates its formula on a supplied 2026
# first-eligibility flag and imports only the 2026 bend points.
PIA_CANDIDATE_ELIGIBILITY_YEAR = 2026
# The 415(b) candidate counts computation base years after its 1950
# ``elapsed_years_baseline_year`` parameter.
FIRST_COMPUTATION_BASE_YEAR = 1951
REQUEST_SCHEMA = "axiom-rules-engine/lifetime-request/v2"
RESPONSE_SCHEMA = "axiom-rules-engine/lifetime-response/v2"
ARTIFACT_AIME_PIA = "aime_pia"
ARTIFACT_AIME_ONLY = "aime_only"
CANDIDATE_STATUS = (
    "unaccepted encoder candidates: 42 USC 415(b) AIME and a conditional "
    "2026-cohort 415(a) ordinary PIA; the combined graph's import-proof "
    "metadata is stale and proof validation has not passed"
)

# Case A supplied these conditions as scoped assumptions, not findings.
SCOPED_ASSUMPTIONS: Mapping[str, bool] = {
    "individual_is_entitled_to_old_age_insurance_benefit": True,
    "individual_is_entitled_to_disability_insurance_benefit": False,
    "individual_previously_entitled_to_disability_insurance_benefit": False,
    (
        "at_least_twelve_consecutive_months_without_disability_or_old_age_"
        "benefit_before_current_eligibility"
    ): False,
    "computation_base_year_is_entirely_in_period_of_disability": False,
    "elapsed_year_is_partly_in_period_of_disability": False,
}

# Reviewed identities of the engine and candidate files that reproduced the
# published SSA Case A AIME ($5,825) and initial PIA ($2,609.80).
REVIEWED_ENGINE_SOURCE_COMMIT = "49f2225c2788b242f961e1eaee41f75cf703f685"
REVIEWED_PINS: Mapping[str, str] = {
    "engine": (
        "e41161754874789a84d609f243e1db92948fd19806555bc942ab2048946c8dea"
    ),
    "engine_provenance_receipt": (
        "469d13fd0ecfa9995f128f0129e695f47111d3baebd1e31466c2f1e0162ecd3c"
    ),
    "engine_binding_manifest": (
        "0b6515e5e6f2650899c757a3683c8a9faa1819f05bef857a942b278ddda196c0"
    ),
    ARTIFACT_AIME_PIA: (
        "10d32e4284f64f63a62c4e256ed059cb49e2d1b57118c7b8004bd9076c46f3a8"
    ),
    ARTIFACT_AIME_ONLY: (
        "ed1fdb444c41e88944e76edb9fe66d6dc9849876ae8265d9a860eb8c76fb5643"
    ),
    "aime_pia_compile_receipt": (
        "b5dc18fe554da11c065181d3b111bb8762487c7b6a2b0d5c80edfd26a387466a"
    ),
    "module:us/statutes/42/415/b.yaml": (
        "24ddf3b6810f68a77ae0f9295f98994ed4a3d24a46a94609045296661a477318"
    ),
    "module:us/statutes/42/415/a.yaml": (
        "81487dbc6115d7513f39e7de714f8bf6886cbb06562a5784336f93617c616dda"
    ),
    "module:us/policies/ssa/pia-bend-points/2026.yaml": (
        "dd39d3ceda711c0eca7e2a752561c368efd59d64dbf35343b16d1cd5e7c882e0"
    ),
    "aime_only_source:us/statutes/42/415/b.yaml": (
        "24ddf3b6810f68a77ae0f9295f98994ed4a3d24a46a94609045296661a477318"
    ),
}
ENGINE_ROOT_ENV = "POPULACE_DYNAMICS_AXIOM_ENGINE_ROOT"
EVIDENCE_DIR_ENV = "POPULACE_DYNAMICS_AXIOM_EVIDENCE_DIR"
DEFAULT_ENGINE_ROOT = "~/TheAxiomFoundation/_worktrees/" + (
    "dynamics-lazy-lifetime-20260922"
)
DEFAULT_EVIDENCE_DIR = "~/microcosm-launch-evidence/" + (
    "dynasim-parity-20260909/parallel-oasdi-20260920/encoder-recovery"
)

# The engine parses decimal inputs with rust_decimal's
# ``Decimal::from_str_exact`` (axiom-rules-engine src/lifetime_api.rs), which
# rejects the long exact expansions of most fractional binary64 values.
# Converting projected binary64 amounts is therefore an explicit caller
# choice, recorded on every row.
BINARY64_EXACT = "exact_binary64"
BINARY64_SHORTEST_ROUND_TRIP = "shortest_round_trip_binary64"
BINARY64_ENCODINGS = (BINARY64_EXACT, BINARY64_SHORTEST_ROUND_TRIP)

_DECIMAL_TEXT = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SUBPROCESS_ENV = {"PATH": "/usr/bin:/bin"}


class BenefitBridgeRefusal(ValueError):
    """The rule needs an input this person lacks; nothing was guessed."""

    def __init__(
        self,
        subject: str,
        reasons: Sequence[str],
        *,
        gaps: Mapping[str, Sequence[int]] | None = None,
    ) -> None:
        self.subject = subject
        self.reasons = tuple(reasons)
        self.gaps = {
            name: tuple(years) for name, years in (gaps or {}).items()
        }
        if not self.reasons:
            raise ValueError("a refusal needs at least one reason")
        super().__init__(f"{subject}: " + "; ".join(self.reasons))


class AxiomExecutionError(RuntimeError):
    """The engine failed or returned a response that does not validate."""


class BindingMismatch(RuntimeError):
    """A bound engine, artifact or candidate file is absent or changed."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{label} must be an integer without coercion")
    return int(value)


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _amount(value: object, label: str) -> Decimal:
    """Accept exact decimal inputs only; binary floats need explicit bits."""
    if isinstance(value, bool):
        raise TypeError(f"{label} cannot be a boolean")
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, Integral):
        amount = Decimal(int(value))
    elif type(value) is str and _DECIMAL_TEXT.fullmatch(value):
        amount = Decimal(value)
    else:
        raise TypeError(
            f"{label} must be a Decimal, integer or plain decimal string"
        )
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return amount


def _decimal_text(amount: Decimal) -> str:
    """Plain decimal text accepted by the engine, never exponent notation."""
    text = "0" if amount == 0 else format(amount, "f")
    if not _DECIMAL_TEXT.fullmatch(text):
        raise ValueError(f"amount {amount!r} has no plain decimal form")
    return text


def binary64_decimal(amount_hex: str, encoding: str) -> Decimal:
    """Decimal for binary64 source bits under an explicit encoding.

    ``exact_binary64`` is the exact value of the bits.  The
    ``shortest_round_trip_binary64`` encoding is Python's shortest decimal
    that converts back to the same bits; it can differ from the exact value
    by less than half a unit in the last binary64 place.
    """
    if type(amount_hex) is not str:
        raise TypeError("binary64 amount must be float.hex() text")
    value = float.fromhex(amount_hex)
    if value.hex() != amount_hex:
        raise ValueError("binary64 amount must be canonical float.hex() text")
    if encoding == BINARY64_EXACT:
        return Decimal(value)
    if encoding == BINARY64_SHORTEST_ROUND_TRIP:
        shortest = Decimal(repr(value))
        if shortest == shortest.to_integral_value():
            shortest = shortest.quantize(Decimal(1))
        if float(shortest) != value:
            raise ValueError("shortest decimal does not round-trip")
        return shortest
    raise ValueError(f"unsupported binary64 encoding {encoding!r}")


def year_ranges(years: Iterable[int]) -> str:
    """Compress sorted years into ``1974-2013, 2023`` style text."""
    ordered = sorted(set(years))
    if not ordered:
        return "none"
    spans, start, previous = [], ordered[0], ordered[0]
    for year in ordered[1:]:
        if year != previous + 1:
            spans.append((start, previous))
            start = year
        previous = year
    spans.append((start, previous))
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)


def _year_period(year: int) -> dict[str, str]:
    return {
        "period_kind": "custom",
        "name": "calendar_year",
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
    }


@dataclass(frozen=True)
class AnnualSeries:
    """Exact published decimal strings by calendar year, never floats."""

    label: str
    values: tuple[tuple[int, str], ...]
    source_sha256: str | None = None

    def __post_init__(self) -> None:
        _text(self.label, "series label")
        if self.source_sha256 is not None and (
            type(self.source_sha256) is not str
            or not _SHA256.fullmatch(self.source_sha256)
        ):
            raise ValueError("series source digest must be SHA-256 hex")
        rows = []
        for year, value in self.values:
            year = _integer(year, "series year")
            if type(value) is not str or not _DECIMAL_TEXT.fullmatch(value):
                raise ValueError(f"{year} value must be a decimal string")
            if Decimal(value) <= 0:
                raise ValueError(f"{year} value must be positive")
            rows.append((year, value))
        rows.sort()
        if len({year for year, _ in rows}) != len(rows):
            raise ValueError("series years must be unique")
        object.__setattr__(self, "values", tuple(rows))

    @classmethod
    def from_mapping(
        cls,
        label: str,
        values: Mapping[int, str],
        *,
        source_sha256: str | None = None,
    ) -> AnnualSeries:
        return cls(label, tuple(values.items()), source_sha256)

    def get(self, year: int) -> str | None:
        return dict(self.values).get(year)

    def document(self) -> dict[str, object]:
        years = [year for year, _ in self.values]
        return {
            "label": self.label,
            "source_sha256": self.source_sha256,
            "years": year_ranges(years),
        }


@dataclass(frozen=True)
class EarningsRow:
    """One annual nominal amount as transported, with its provenance."""

    year: int
    amount: Decimal
    source: str
    synthetic: bool
    amount_hex: str | None = None
    encoding: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "year", _integer(self.year, "row year"))
        object.__setattr__(self, "amount", _amount(self.amount, "amount"))
        _text(self.source, "row source")
        if type(self.synthetic) is not bool:
            raise TypeError("synthetic must be an explicit bool")
        if self.amount_hex is None:
            if self.encoding is not None:
                raise ValueError("an encoding needs binary64 source bits")
        elif binary64_decimal(self.amount_hex, self.encoding) != self.amount:
            raise ValueError("amount must equal its encoded binary64 bits")

    def document(self) -> dict[str, object]:
        return {
            "year": self.year,
            "amount": _decimal_text(self.amount),
            "source": self.source,
            "synthetic": self.synthetic,
            "amount_hex": self.amount_hex,
            "encoding": self.encoding,
        }


@dataclass(frozen=True)
class CallerSuppliedHistory:
    """An explicit annual history supplied by the caller, labeled at source.

    Use it for pre-projection years the retained projection does not
    contain.  Invented rows must set ``synthetic=True``; the flag travels
    into every result.
    """

    label: str
    synthetic: bool
    amounts: tuple[tuple[int, Decimal], ...]

    def __post_init__(self) -> None:
        _text(self.label, "supplied history label")
        if type(self.synthetic) is not bool:
            raise TypeError("synthetic must be an explicit bool")
        rows = sorted(
            (_integer(year, "supplied year"), _amount(amount, "amount"))
            for year, amount in self.amounts
        )
        if len({year for year, _ in rows}) != len(rows):
            raise ValueError("supplied years must be unique")
        object.__setattr__(self, "amounts", tuple(rows))

    @classmethod
    def from_mapping(
        cls,
        label: str,
        amounts: Mapping[int, object],
        *,
        synthetic: bool,
    ) -> CallerSuppliedHistory:
        return cls(label, synthetic, tuple(amounts.items()))

    def rows(self) -> tuple[EarningsRow, ...]:
        prefix = (
            "synthetic_caller_supplied"
            if self.synthetic
            else ("caller_supplied")
        )
        return tuple(
            EarningsRow(year, amount, f"{prefix}:{self.label}", self.synthetic)
            for year, amount in self.amounts
        )


@dataclass(frozen=True)
class LeadingGapAcknowledgement:
    """Explicit acceptance that leading elapsed-window years are absent.

    Only for sources (such as SSA's published worked examples) that list no
    earlier rows.  The years are recorded as unsupplied; the engine receives
    no rows for them, so they cannot enter its top-N selection.
    """

    years: tuple[int, ...]
    statement: str

    def __post_init__(self) -> None:
        years = tuple(sorted(_integer(y, "gap year") for y in self.years))
        if not years or years != tuple(range(years[0], years[-1] + 1)):
            raise ValueError("acknowledged years must be one contiguous run")
        _text(self.statement, "acknowledgement statement")
        object.__setattr__(self, "years", years)


@dataclass(frozen=True)
class OrdinaryRetirementDeterminations:
    """Calendar facts the candidates take as inputs but do not derive."""

    birth_year: int
    first_old_age_entitlement_year: int
    year_attained_age_21: int
    year_attained_age_62: int
    indexing_year: int
    death_or_later_sentinel_year: int
    derivations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "birth_year",
            "first_old_age_entitlement_year",
            "year_attained_age_21",
            "year_attained_age_62",
            "indexing_year",
            "death_or_later_sentinel_year",
        ):
            object.__setattr__(self, name, _integer(getattr(self, name), name))
        reasons = []
        if self.year_attained_age_62 != self.year_attained_age_21 + 41:
            reasons.append("ages 21 and 62 must be attained 41 years apart")
        if self.first_old_age_entitlement_year < self.year_attained_age_62:
            reasons.append(
                "ordinary old-age entitlement year "
                f"{self.first_old_age_entitlement_year} precedes the year "
                f"of attaining 62 ({self.year_attained_age_62})"
            )
        if self.indexing_year >= self.first_old_age_entitlement_year:
            reasons.append("indexing year must precede entitlement")
        if (
            self.death_or_later_sentinel_year
            < self.first_old_age_entitlement_year
        ):
            reasons.append(
                "death-or-later sentinel precedes entitlement; this bridge "
                "supports living ordinary old-age entitlement only"
            )
        if reasons:
            raise BenefitBridgeRefusal(
                f"birth year {self.birth_year}", reasons
            )
        object.__setattr__(self, "derivations", tuple(self.derivations))

    @classmethod
    def from_birth_year(
        cls, birth_year: int, entitlement_year: int
    ) -> OrdinaryRetirementDeterminations:
        """Apply the retained Case A/B calendar conventions to a birth year."""
        birth_year = _integer(birth_year, "birth year")
        entitlement_year = _integer(entitlement_year, "entitlement year")
        return cls(
            birth_year,
            entitlement_year,
            birth_year + 21,
            birth_year + 62,
            birth_year + 60,
            entitlement_year,
            (
                "year_individual_attained_age_21 = birth year + 21",
                "year_individual_attained_age_62 = birth year + 62",
                "indexing_year_for_aime = year of attaining 62 minus 2; "
                "the 415(b) candidate defers indexing-year selection, and "
                "this matches the retained Case A (2024) and Case B (2019) "
                "inputs",
                "year_of_death_or_later_sentinel = first entitlement year, "
                "a later-boundary sentinel as in the Case A/B runners, not "
                "a death assertion",
                "birth year only: SSA treats an age as attained on the day "
                "before the birthday (retained POMS RS 00615.015 extract), "
                "so a January 1 birth would attain each age one calendar "
                "year earlier; exact birth dates are unavailable",
            ),
        )

    def document(self) -> dict[str, object]:
        return {
            "birth_year": self.birth_year,
            "first_old_age_entitlement_year": (
                self.first_old_age_entitlement_year
            ),
            "year_attained_age_21": self.year_attained_age_21,
            "year_attained_age_62": self.year_attained_age_62,
            "indexing_year": self.indexing_year,
            "death_or_later_sentinel_year": self.death_or_later_sentinel_year,
            "derivations": list(self.derivations),
        }


@dataclass(frozen=True)
class PreparedRequest:
    """A validated lifetime request and everything recorded about it."""

    person_id: str
    request: Mapping[str, object]
    wire: bytes
    artifact_role: str
    outputs: tuple[str, ...]
    rows: tuple[EarningsRow, ...]
    determinations: OrdinaryRetirementDeterminations
    recorded_gaps: tuple[Mapping[str, object], ...]
    wage_index: AnnualSeries
    notes: tuple[str, ...] = ()

    @property
    def pia_requested(self) -> bool:
        return PIA_OUTPUT in self.outputs

    @property
    def calculation_year(self) -> int:
        return self.determinations.first_old_age_entitlement_year

    @property
    def request_sha256(self) -> str:
        return _sha256_bytes(self.wire)


def _window_start(determinations: OrdinaryRetirementDeterminations) -> int:
    return max(
        FIRST_COMPUTATION_BASE_YEAR, determinations.year_attained_age_21 + 1
    )


def _missing_wage_index_years(
    years: Iterable[int], indexing_year: int, wage_index: AnnualSeries
) -> tuple[int, ...]:
    needed = {year for year in years if year <= indexing_year}
    needed.add(indexing_year)
    return tuple(sorted(y for y in needed if wage_index.get(y) is None))


def prepare_request(
    person_id: str,
    rows: Sequence[EarningsRow],
    determinations: OrdinaryRetirementDeterminations,
    wage_index: AnnualSeries,
    *,
    contribution_base: AnnualSeries | None = None,
    leading_gap: LeadingGapAcknowledgement | None = None,
    notes: Sequence[str] = (),
) -> PreparedRequest:
    """Build one person's request exactly as the Case A runner did.

    Every year from the start of the elapsed-year window (the year after
    attaining 21, and after 1950) through the year before entitlement must be
    supplied, unless a leading run of those years is explicitly acknowledged.
    Computation base years before the elapsed-year window may be absent;
    they are recorded, never filled.
    """
    _text(person_id, "person id")
    if type(determinations) is not OrdinaryRetirementDeterminations:
        raise TypeError("explicit OrdinaryRetirementDeterminations required")
    if type(wage_index) is not AnnualSeries:
        raise TypeError("explicit wage-index AnnualSeries required")
    rows = tuple(sorted(rows, key=lambda row: row.year))
    if any(type(row) is not EarningsRow for row in rows):
        raise TypeError("EarningsRow values required")
    entitlement = determinations.first_old_age_entitlement_year
    index_year = determinations.indexing_year
    reasons: list[str] = []
    gaps: dict[str, tuple[int, ...]] = {}
    years = [row.year for row in rows]
    if len(set(years)) != len(years):
        raise ValueError("each year may be supplied once")
    outside = [
        y for y in years if not FIRST_COMPUTATION_BASE_YEAR <= y < entitlement
    ]
    if outside:
        reasons.append(
            f"years {year_ranges(outside)} are not computation base years "
            f"before the {entitlement} entitlement year"
        )
    window = range(_window_start(determinations), entitlement)
    supplied = set(years)
    missing = [y for y in window if y not in supplied]
    acknowledged: tuple[int, ...] = ()
    if leading_gap is not None:
        if type(leading_gap) is not LeadingGapAcknowledgement:
            raise TypeError("LeadingGapAcknowledgement required")
        first = min(supplied) if supplied else entitlement
        leading = tuple(y for y in missing if y < first)
        if leading_gap.years != leading or not leading:
            reasons.append(
                "acknowledged years "
                f"{year_ranges(leading_gap.years)} do not equal the "
                f"unsupplied leading elapsed-window years "
                f"{year_ranges(leading)}"
            )
        else:
            acknowledged = leading
    missing = [y for y in missing if y not in acknowledged]
    if missing:
        reasons.append(
            f"required years {year_ranges(missing)} are absent; the "
            f"elapsed-year window runs {window.start}-{window.stop - 1} and "
            "no year may be padded"
        )
        gaps["missing_required_years"] = tuple(missing)
    if years:
        holes = [
            y for y in range(min(years), max(years) + 1) if y not in supplied
        ]
        holes = [y for y in holes if y not in missing]
        if holes:
            reasons.append(f"interior years {year_ranges(holes)} are absent")
            gaps["missing_interior_years"] = tuple(holes)
    else:
        reasons.append("no earnings rows were supplied")
    missing_index = _missing_wage_index_years(
        (supplied | set(window)) - set(acknowledged), index_year, wage_index
    )
    if missing_index:
        reasons.append(
            "national average wage index values are absent for "
            f"{year_ranges(missing_index)} (indexing year {index_year})"
        )
        gaps["missing_wage_index_years"] = missing_index
    recorded: list[dict[str, object]] = []
    if contribution_base is not None:
        if type(contribution_base) is not AnnualSeries:
            raise TypeError("contribution base must be an AnnualSeries")
        unchecked, above = [], []
        for row in rows:
            if row.amount == 0:
                continue
            ceiling = contribution_base.get(row.year)
            if ceiling is None:
                unchecked.append(row.year)
            elif row.amount > Decimal(ceiling):
                above.append(row.year)
        if unchecked:
            reasons.append(
                "no contribution and benefit base is available to check "
                f"nonzero amounts in {year_ranges(unchecked)}"
            )
            gaps["unchecked_creditable_ceiling_years"] = tuple(unchecked)
        if above:
            reasons.append(
                f"amounts in {year_ranges(above)} exceed the contribution and "
                "benefit base; the bridge does not limit creditable earnings"
            )
            gaps["above_creditable_ceiling_years"] = tuple(above)
    else:
        recorded.append(
            {
                "kind": "creditable_ceiling_not_checked",
                "effect": "no contribution and benefit base series was "
                "supplied, so amounts were not checked against it",
            }
        )
    if reasons:
        raise BenefitBridgeRefusal(person_id, reasons, gaps=gaps)

    first_supplied = min(years)
    early = range(
        max(FIRST_COMPUTATION_BASE_YEAR, determinations.birth_year),
        min(first_supplied, window.start),
    )
    if len(early):
        recorded.append(
            {
                "kind": "computation_base_years_before_elapsed_window_"
                "not_supplied",
                "years": year_ranges(early),
                "effect": "no engine rows; these years cannot enter the "
                "top-N selection",
            }
        )
    if acknowledged:
        recorded.append(
            {
                "kind": "acknowledged_unsupplied_elapsed_window_years",
                "years": year_ranges(acknowledged),
                "statement": leading_gap.statement,
                "effect": "no engine rows; these years cannot enter the "
                "top-N selection",
            }
        )
    pia = determinations.year_attained_age_62 == PIA_CANDIDATE_ELIGIBILITY_YEAR
    outputs = (AIME_OUTPUT, PIA_OUTPUT) if pia else (AIME_OUTPUT,)
    batches = []
    for row in rows:
        values: dict[str, tuple[str, object]] = {
            name: ("bool", value) for name, value in SCOPED_ASSUMPTIONS.items()
        }
        values.update(
            {
                "computation_base_year": ("integer", row.year),
                "creditable_earnings_for_computation_base_year": (
                    "decimal",
                    _decimal_text(row.amount),
                ),
                "national_average_wage_index_for_indexing_year": (
                    "decimal",
                    wage_index.get(index_year),
                ),
                "indexing_year_for_aime": ("integer", index_year),
                "year_individual_attained_age_21": (
                    "integer",
                    determinations.year_attained_age_21,
                ),
                "year_individual_attained_age_62": (
                    "integer",
                    determinations.year_attained_age_62,
                ),
                "year_of_death_or_later_sentinel": (
                    "integer",
                    determinations.death_or_later_sentinel_year,
                ),
                "year_of_first_old_age_entitlement": ("integer", entitlement),
            }
        )
        if row.year <= index_year:
            # Case A/B omit the per-year index after the indexing year.
            values["national_average_wage_index_for_computation_base_year"] = (
                "decimal",
                wage_index.get(row.year),
            )
        inputs = {
            AIME_INPUT_PREFIX + name: {"kind": kind, "values": [value]}
            for name, (kind, value) in values.items()
        }
        if pia:
            inputs[PIA_COHORT_INPUT] = {"kind": "bool", "values": [True]}
        batches.append(
            {"row_count": 1, "entity_ids": [person_id], "inputs": inputs}
        )
    calculation = _year_period(entitlement)
    request = {
        "schema": REQUEST_SCHEMA,
        "entity": "Person",
        "arithmetic": "decimal",
        "periods": [_year_period(row.year) for row in rows],
        "batches": batches,
        "calculation_period": calculation,
        "outputs": list(outputs),
        "output_period": calculation,
    }
    wire = (
        json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return PreparedRequest(
        person_id,
        request,
        wire,
        ARTIFACT_AIME_PIA if pia else ARTIFACT_AIME_ONLY,
        outputs,
        rows,
        determinations,
        tuple(recorded),
        wage_index,
        tuple(notes),
    )


@dataclass(frozen=True)
class BoundFile:
    """A file whose SHA-256 must match before and after every execution."""

    role: str
    path: Path
    sha256: str

    def __post_init__(self) -> None:
        _text(self.role, "bound role")
        object.__setattr__(self, "path", Path(self.path))
        if type(self.sha256) is not str or not _SHA256.fullmatch(self.sha256):
            raise ValueError("bound digest must be lowercase SHA-256 hex")

    def document(self) -> dict[str, str]:
        return {
            "role": self.role,
            "path": str(self.path),
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class AxiomEngineBinding:
    """The engine binary, compiled artifacts and candidate sources in use."""

    engine: BoundFile
    artifacts: tuple[BoundFile, ...]
    supporting: tuple[BoundFile, ...]
    engine_source_commit: str
    candidate_status: str = CANDIDATE_STATUS
    candidates_accepted: bool = False
    engine_manifest_role: str | None = None
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        roles = [
            f.role for f in (self.engine, *self.artifacts, *self.supporting)
        ]
        if len(set(roles)) != len(roles):
            raise ValueError("bound roles must be unique")
        if {a.role for a in self.artifacts} != {
            ARTIFACT_AIME_PIA,
            ARTIFACT_AIME_ONLY,
        }:
            raise ValueError("aime_pia and aime_only artifacts are required")
        if type(self.candidates_accepted) is not bool:
            raise TypeError("candidates_accepted must be an explicit bool")
        _text(self.engine_source_commit, "engine source commit")

    @property
    def files(self) -> tuple[BoundFile, ...]:
        return (self.engine, *self.artifacts, *self.supporting)

    def artifact(self, role: str) -> BoundFile:
        for artifact in self.artifacts:
            if artifact.role == role:
                return artifact
        raise KeyError(role)

    def missing_files(self) -> tuple[Path, ...]:
        return tuple(f.path for f in self.files if not f.path.is_file())

    def verify(self) -> None:
        """Fail closed on any absent or changed file, or manifest drift."""
        problems = []
        for bound in self.files:
            if bound.path.is_symlink() or not bound.path.is_file():
                problems.append(f"{bound.role} is absent: {bound.path}")
            elif _sha256_file(bound.path) != bound.sha256:
                problems.append(f"{bound.role} digest changed: {bound.path}")
        if not problems and self.engine_manifest_role is not None:
            manifest = json.loads(
                next(
                    f
                    for f in self.supporting
                    if f.role == self.engine_manifest_role
                ).path.read_text()
            )
            receipt = next(
                (
                    f.sha256
                    for f in self.supporting
                    if f.role == "engine_provenance_receipt"
                ),
                None,
            )
            if (
                manifest.get("binary_sha256") != self.engine.sha256
                or manifest.get("source_commit") != self.engine_source_commit
                or manifest.get("official_no_build_verified") is not True
                or (receipt and manifest.get("receipt_sha256") != receipt)
            ):
                problems.append("engine binding manifest does not bind engine")
        if problems:
            raise BindingMismatch("; ".join(problems))

    def document(self) -> dict[str, object]:
        return {
            "engine": self.engine.document(),
            "engine_source_commit": self.engine_source_commit,
            "artifacts": [a.document() for a in self.artifacts],
            "supporting": [f.document() for f in self.supporting],
            "candidates_accepted": self.candidates_accepted,
            "candidate_status": self.candidate_status,
        }


def reviewed_case_a_binding(
    engine_root: str | os.PathLike[str] | None = None,
    evidence_dir: str | os.PathLike[str] | None = None,
) -> AxiomEngineBinding:
    """Bind the exact engine and candidates that reproduced Case A.

    ``evidence_dir`` is the retained ``encoder-recovery`` directory.  The
    locations default to this machine's layout and may be overridden by
    ``POPULACE_DYNAMICS_AXIOM_ENGINE_ROOT`` and
    ``POPULACE_DYNAMICS_AXIOM_EVIDENCE_DIR``; the digests may not.
    """
    root = Path(
        engine_root or os.environ.get(ENGINE_ROOT_ENV) or DEFAULT_ENGINE_ROOT
    ).expanduser()
    evidence = Path(
        evidence_dir
        or os.environ.get(EVIDENCE_DIR_ENV)
        or DEFAULT_EVIDENCE_DIR
    ).expanduser()
    case_a = evidence / "ssa-aime-pia-first-comparison-20260922"
    integrated = case_a / "integrated-experiment"
    rulespec = integrated / "rulespec-us/us"
    replay = evidence / "replay-415-b-nested-lifetime-20260922"
    binary = root / "target/release/axiom-rules-engine"

    def bound(role: str, path: Path) -> BoundFile:
        return BoundFile(role, path, REVIEWED_PINS[role])

    return AxiomEngineBinding(
        engine=bound("engine", binary),
        artifacts=(
            bound(ARTIFACT_AIME_PIA, integrated / "aime-pia.compiled.json"),
            bound(ARTIFACT_AIME_ONLY, replay / "compile/415-b.compiled.json"),
        ),
        supporting=(
            bound(
                "engine_provenance_receipt",
                binary.with_suffix(".provenance.json"),
            ),
            bound(
                "engine_binding_manifest", case_a / "lazy-engine-binding.json"
            ),
            bound(
                "aime_pia_compile_receipt", integrated / "compile-receipt.json"
            ),
            bound(
                "module:us/statutes/42/415/b.yaml",
                rulespec / "statutes/42/415/b.yaml",
            ),
            bound(
                "module:us/statutes/42/415/a.yaml",
                rulespec / "statutes/42/415/a.yaml",
            ),
            bound(
                "module:us/policies/ssa/pia-bend-points/2026.yaml",
                rulespec / "policies/ssa/pia-bend-points/2026.yaml",
            ),
            bound(
                "aime_only_source:us/statutes/42/415/b.yaml",
                replay / "rulespec-us/us/statutes/42/415/b.yaml",
            ),
        ),
        engine_source_commit=REVIEWED_ENGINE_SOURCE_COMMIT,
        engine_manifest_role="engine_binding_manifest",
    )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON constant {value}")


@dataclass(frozen=True)
class ParsedResponse:
    engine_version: str
    values: Mapping[str, Decimal]
    selected_versions: tuple[Mapping[str, object], ...]


def parse_lifetime_response(
    request: Mapping[str, object], stdout: bytes
) -> ParsedResponse:
    """Validate a one-person response against its request, then read it."""
    try:
        response = json.loads(
            stdout,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (ValueError, UnicodeDecodeError) as exc:
        raise AxiomExecutionError(
            f"response is not valid JSON: {exc}"
        ) from exc
    fields = {
        "schema",
        "engine_version",
        "artifact_format_version",
        "arithmetic",
        "entity",
        "row_count",
        "entity_ids",
        "periods",
        "calculation_period",
        "reference_period",
        "output_period",
        "selected_versions",
        "outputs",
    }
    if not isinstance(response, dict) or set(response) != fields:
        raise AxiomExecutionError("response fields do not match schema v2")
    batch = request["batches"][-1]
    expected = {
        "schema": RESPONSE_SCHEMA,
        "artifact_format_version": 2,
        "arithmetic": "decimal",
        "entity": request["entity"],
        "row_count": batch["row_count"],
        "entity_ids": batch["entity_ids"],
        "periods": request["periods"],
        "calculation_period": request["calculation_period"],
        "reference_period": request["output_period"],
        "output_period": request["output_period"],
    }
    for name, wanted in expected.items():
        if response[name] != wanted or type(response[name]) is not type(
            wanted
        ):
            raise AxiomExecutionError(
                f"response {name} does not match request"
            )
    version = response["engine_version"]
    if type(version) is not str or not version:
        raise AxiomExecutionError("response engine_version is invalid")
    outputs = response["outputs"]
    requested = list(request["outputs"])
    if not isinstance(outputs, dict) or set(outputs) != set(requested):
        raise AxiomExecutionError("response outputs differ from the request")
    selected = response["selected_versions"]
    if not isinstance(selected, list) or not selected:
        raise AxiomExecutionError("response selected_versions are missing")
    calculation_start = request["calculation_period"]["start"]
    derived = {}
    for item in selected:
        if not isinstance(item, dict) or item.get("kind") not in (
            "derived",
            "unversioned_derived",
            "parameter",
        ):
            raise AxiomExecutionError("response selected version is invalid")
        if item["kind"] == "derived":
            start, end = item.get("effective_from"), item.get("effective_to")
            if (
                type(start) is not str
                or start > calculation_start
                or (
                    end is not None
                    and (type(end) is not str or end < calculation_start)
                )
            ):
                raise AxiomExecutionError(
                    "selected version does not cover the calculation date"
                )
        if item["kind"] != "parameter" and item.get("id") is not None:
            derived[item["id"]] = item.get("name")
    values = {}
    for reference in requested:
        output = outputs[reference]
        if not isinstance(output, dict) or set(output) != {
            "id",
            "name",
            "dtype",
            "unit",
            "column",
        }:
            raise AxiomExecutionError(f"output {reference} is malformed")
        column = output["column"]
        if (
            output["id"] != reference
            or derived.get(reference) != output["name"]
            or output["dtype"] != "decimal"
            or output["unit"] != "USD"
            or not isinstance(column, dict)
            or set(column) != {"kind", "values"}
            or column["kind"] != "decimal"
            or not isinstance(column["values"], list)
            or len(column["values"]) != 1
        ):
            raise AxiomExecutionError(f"output {reference} is malformed")
        text = column["values"][0]
        if type(text) is not str or not _DECIMAL_TEXT.fullmatch(text):
            raise AxiomExecutionError(f"output {reference} is not a decimal")
        try:
            values[reference] = Decimal(text)
        except InvalidOperation as exc:
            raise AxiomExecutionError(f"output {reference} invalid") from exc
    return ParsedResponse(version, values, tuple(selected))


@dataclass(frozen=True)
class AxiomBenefitResult:
    """Engine outputs for one person, with inputs and execution provenance."""

    person_id: str
    aime: Decimal
    ordinary_pia_before_cola: Decimal | None
    pia_status: str
    prepared: PreparedRequest
    engine_version: str
    stdout_sha256: str
    stderr: str
    binding: AxiomEngineBinding
    selected_versions: tuple[Mapping[str, object], ...] = field(repr=False)
    stdout: bytes = field(default=b"", repr=False, compare=False)

    def document(self) -> dict[str, object]:
        prepared = self.prepared
        artifact = self.binding.artifact(prepared.artifact_role)
        return {
            "person_id": self.person_id,
            "aime": _decimal_text(self.aime),
            "ordinary_pia_before_cola": (
                None
                if self.ordinary_pia_before_cola is None
                else _decimal_text(self.ordinary_pia_before_cola)
            ),
            "pia_status": self.pia_status,
            "calculation_year": prepared.calculation_year,
            "determinations": prepared.determinations.document(),
            "scoped_assumptions": dict(SCOPED_ASSUMPTIONS),
            "earnings_rows": [row.document() for row in prepared.rows],
            "synthetic_rows": sum(row.synthetic for row in prepared.rows),
            "recorded_gaps": [dict(gap) for gap in prepared.recorded_gaps],
            "notes": list(prepared.notes),
            "wage_index": prepared.wage_index.document(),
            "provenance": {
                "engine_path": str(self.binding.engine.path),
                "engine_sha256": self.binding.engine.sha256,
                "engine_source_commit": self.binding.engine_source_commit,
                "engine_version": self.engine_version,
                "artifact_role": prepared.artifact_role,
                "artifact_path": str(artifact.path),
                "artifact_sha256": artifact.sha256,
                "module_sha256": {
                    f.role: f.sha256
                    for f in self.binding.supporting
                    if "module:" in f.role or "source:" in f.role
                },
                "candidates_accepted": self.binding.candidates_accepted,
                "candidate_status": self.binding.candidate_status,
                "outputs_requested": list(prepared.outputs),
                "request_sha256": prepared.request_sha256,
                "stdout_sha256": self.stdout_sha256,
                "stderr": self.stderr,
                "selected_versions": [dict(v) for v in self.selected_versions],
                "policy_arithmetic_in_bridge": False,
            },
        }


Runner = Callable[[Sequence[str], bytes, float], tuple[int, bytes, bytes]]


def subprocess_runner(
    argv: Sequence[str], wire: bytes, timeout: float
) -> tuple[int, bytes, bytes]:
    """Run the engine exactly as the Case A runner did."""
    process = subprocess.run(
        list(argv),
        input=wire,
        capture_output=True,
        timeout=timeout,
        env=dict(_SUBPROCESS_ENV),
        check=False,
    )
    return process.returncode, process.stdout, process.stderr


def execute_request(
    prepared: PreparedRequest,
    binding: AxiomEngineBinding,
    *,
    runner: Runner | None = None,
) -> AxiomBenefitResult:
    """Verify the binding, run the engine once, verify again, then parse."""
    if type(prepared) is not PreparedRequest:
        raise TypeError("PreparedRequest required")
    if type(binding) is not AxiomEngineBinding:
        raise TypeError("AxiomEngineBinding required")
    binding.verify()
    artifact = binding.artifact(prepared.artifact_role)
    argv = (
        str(binding.engine.path),
        "run-lifetime",
        "--artifact",
        str(artifact.path),
    )
    try:
        code, stdout, stderr = (runner or subprocess_runner)(
            argv, prepared.wire, binding.timeout_seconds
        )
    except subprocess.TimeoutExpired as exc:
        raise AxiomExecutionError(
            f"{prepared.person_id}: engine timed out"
        ) from exc
    binding.verify()
    error_text = stderr.decode("utf-8", errors="replace").strip()
    if code != 0:
        message = error_text or stdout.decode("utf-8", "replace").strip()
        try:
            message = json.loads(message)["message"]
        except (ValueError, KeyError, TypeError):
            pass
        raise AxiomExecutionError(
            f"{prepared.person_id}: engine exited {code}: {message}"
        )
    parsed = parse_lifetime_response(prepared.request, stdout)
    pia = parsed.values.get(PIA_OUTPUT)
    status = (
        "computed_by_2026_cohort_candidate"
        if prepared.pia_requested
        else "not_requested: the 415(a) candidate covers only the 2026 "
        "first-eligibility cohort; this person attains 62 in "
        f"{prepared.determinations.year_attained_age_62}"
    )
    return AxiomBenefitResult(
        prepared.person_id,
        parsed.values[AIME_OUTPUT],
        pia,
        status,
        prepared,
        parsed.engine_version,
        _sha256_bytes(stdout),
        error_text,
        binding,
        parsed.selected_versions,
        stdout,
    )


@dataclass(frozen=True)
class PersonDemographics:
    """Birth year and sex taken from a retained mortality-step record."""

    dynamics_person_key: int
    birth_year: int
    sex: str
    derivation: str


def cohort_demographics(
    history: ClosedCohortEarningsHistory,
) -> dict[int, PersonDemographics]:
    """Read ages and sexes that the first retained mortality step recorded.

    The step records ages from the frame for the year before its target
    year (the 2014 frame for the 2015 step).  The engine's convention is
    ``age = year - birth_year``, so each birth year is that year minus age.
    """
    if type(history) is not ClosedCohortEarningsHistory:
        raise TypeError("ClosedCohortEarningsHistory required")
    if not history.transitions:
        raise BenefitBridgeRefusal(
            "cohort",
            [
                "the retained history has no mortality step, so no ages or "
                "birth years are recorded"
            ],
        )
    step = history.transitions[0].mortality
    frame_year = step.target_year - 1
    return {
        row.dynamics_person_key: PersonDemographics(
            row.dynamics_person_key,
            frame_year - row.age,
            row.sex,
            f"{frame_year} minus age {row.age} recorded for the "
            f"{frame_year} frame by the mortality step targeting "
            f"{step.target_year}",
        )
        for row in step.rows
    }


@dataclass(frozen=True)
class ProjectedAmountDeclaration:
    """The caller's explicit statement that projected amounts may be used.

    Forward histories hold labor income whose coverage is not materialized,
    in the history's own unit.  The candidates need creditable earnings in
    USD.  Nothing is converted unless the caller declares it here; the
    statement is recorded verbatim with every result.
    """

    history_unit: str
    treat_as_usd_creditable_earnings: bool
    projected_amounts_synthetic: bool
    statement: str
    binary64_encoding: str = BINARY64_EXACT

    def __post_init__(self) -> None:
        _text(self.history_unit, "history unit")
        _text(self.statement, "declaration statement")
        if self.binary64_encoding not in BINARY64_ENCODINGS:
            raise ValueError("unsupported binary64 encoding")
        for name in (
            "treat_as_usd_creditable_earnings",
            "projected_amounts_synthetic",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be an explicit bool")


def _source_identity(history: ClosedCohortEarningsHistory, key: int) -> str:
    identity = history.baseline.identity_map.reverse_rows([key])[0]
    return f"{identity.logical_type}:{identity.canonical_value}"


def _removal_year(
    history: ClosedCohortEarningsHistory, key: int
) -> int | None:
    for transition in history.transitions:
        step = transition.mortality
        if key in step.pre_keys and key not in step.post_keys:
            return step.target_year
    return None


def prepare_cohort_person(
    history: ClosedCohortEarningsHistory,
    dynamics_person_key: int,
    *,
    demographics: Mapping[int, PersonDemographics],
    entitlement_age: int,
    declaration: ProjectedAmountDeclaration | None,
    wage_index: AnnualSeries,
    contribution_base: AnnualSeries | None = None,
    pre_projection: CallerSuppliedHistory | None = None,
) -> PreparedRequest:
    """Convert one retained person into a request, or refuse with reasons."""
    if type(history) is not ClosedCohortEarningsHistory:
        raise TypeError("ClosedCohortEarningsHistory required")
    key = _integer(dynamics_person_key, "dynamics person key")
    entitlement_age = _integer(entitlement_age, "entitlement age")
    person_id = f"dynamics-person-{key}"
    matches = [h for h in history.histories if h.roster_keys == (key,)]
    if len(matches) != 1:
        raise ValueError(f"{person_id} is outside the original cohort")
    person = matches[0]
    first_projected = person.observations[0].year
    demographic = demographics.get(key)
    if demographic is None or type(demographic.birth_year) is not int:
        raise BenefitBridgeRefusal(
            person_id, ["no birth year is available for this person"]
        )
    reasons: list[str] = []
    gaps: dict[str, tuple[int, ...]] = {}
    if declaration is None:
        reasons.append(
            "projected amounts are forward labor income (coverage "
            f"{person.coverage_status}, unit {person.unit}); the candidate "
            "needs creditable earnings and no ProjectedAmountDeclaration "
            "was supplied"
        )
    else:
        if type(declaration) is not ProjectedAmountDeclaration:
            raise TypeError("ProjectedAmountDeclaration required")
        if declaration.history_unit != person.unit:
            reasons.append(
                f"declaration covers unit {declaration.history_unit}, but "
                f"the history unit is {person.unit}"
            )
        if not declaration.treat_as_usd_creditable_earnings:
            reasons.append(
                "the declaration does not permit projected amounts to be "
                "treated as USD creditable earnings"
            )
    entitlement = demographic.birth_year + entitlement_age
    try:
        determinations = OrdinaryRetirementDeterminations.from_birth_year(
            demographic.birth_year, entitlement
        )
    except BenefitBridgeRefusal as refusal:
        raise BenefitBridgeRefusal(
            person_id, [*reasons, *refusal.reasons], gaps=gaps
        ) from refusal
    removal = _removal_year(history, key)
    if removal is not None and removal <= entitlement:
        reasons.append(
            f"removed by the simulated mortality step targeting {removal}, "
            f"not after the {entitlement} entitlement year; only living "
            "ordinary old-age entitlement is supported"
        )
    projected = [o for o in person.observations if o.year < entitlement]
    if not projected:
        reasons.append(
            f"no projected year ({first_projected}-{person.last_year}) "
            f"precedes the {entitlement} entitlement year, so the "
            "projection contributes no computation base year"
        )
    unavailable = [o.year for o in projected if o.amount_hex is None]
    if unavailable:
        reasons.append(
            f"projected amounts for {year_ranges(unavailable)} are "
            "unavailable (outside the forward-earnings domain)"
        )
        gaps["unavailable_projected_years"] = tuple(unavailable)
    supplement_rows: tuple[EarningsRow, ...] = ()
    if pre_projection is not None:
        if type(pre_projection) is not CallerSuppliedHistory:
            raise TypeError("CallerSuppliedHistory required")
        late = [y for y, _ in pre_projection.amounts if y >= first_projected]
        if late:
            raise ValueError(
                f"pre-projection years must precede {first_projected}: "
                f"{year_ranges(late)}"
            )
        supplement_rows = pre_projection.rows()
    window = range(_window_start(determinations), entitlement)
    supplied = {row.year for row in supplement_rows} | {
        o.year for o in projected
    }
    before = [y for y in window if y < first_projected and y not in supplied]
    after = [y for y in window if y > person.last_year]
    if before:
        reasons.append(
            f"pre-projection years {year_ranges(before)} are required (the "
            f"elapsed-year window starts {window.start}) but absent: the "
            f"retained history begins in {first_projected} and no "
            "caller-supplied history covers them"
        )
        gaps["missing_pre_projection_years"] = tuple(before)
    if after:
        reasons.append(
            f"years {year_ranges(after)} are required before the "
            f"{entitlement} entitlement year but absent: the retained "
            f"history ends in {person.last_year}"
        )
        gaps["missing_post_projection_years"] = tuple(after)
    missing_index = _missing_wage_index_years(
        window, determinations.indexing_year, wage_index
    )
    if missing_index:
        reasons.append(
            "national average wage index values are absent for "
            f"{year_ranges(missing_index)} (indexing year "
            f"{determinations.indexing_year})"
        )
        gaps["missing_wage_index_years"] = missing_index
    if reasons:
        raise BenefitBridgeRefusal(person_id, reasons, gaps=gaps)
    source = f"projected:{person.realization_id}"
    rows = supplement_rows + tuple(
        EarningsRow(
            o.year,
            binary64_decimal(o.amount_hex, declaration.binary64_encoding),
            source,
            declaration.projected_amounts_synthetic,
            o.amount_hex,
            declaration.binary64_encoding,
        )
        for o in projected
    )
    notes = [
        f"source identity {_source_identity(history, key)}; sex "
        f"{demographic.sex}; birth year {demographic.derivation}",
        f"projected amounts transported as USD creditable earnings under "
        f"declaration: {declaration.statement}",
        f"projected binary64 amounts encoded as "
        f"{declaration.binary64_encoding}",
    ]
    excluded = [o.year for o in person.observations if o.year >= entitlement]
    if excluded:
        notes.append(
            f"projected years {year_ranges(excluded)} are not computation "
            f"base years before the {entitlement} entitlement and were not "
            "transported"
        )
    if removal is not None:
        notes.append(
            f"removed by the simulated mortality step targeting {removal}, "
            "after entitlement"
        )
    return prepare_request(
        person_id,
        rows,
        determinations,
        wage_index,
        contribution_base=contribution_base,
        notes=notes,
    )


@dataclass(frozen=True)
class PersonOutcome:
    """Executed result, explicit refusal or engine failure for one person."""

    dynamics_person_key: int
    source_identity: str
    birth_year: int | None
    sex: str | None
    status: str
    result: AxiomBenefitResult | None = None
    reasons: tuple[str, ...] = ()
    gaps: Mapping[str, tuple[int, ...]] = field(default_factory=dict)

    def document(self) -> dict[str, object]:
        return {
            "dynamics_person_key": self.dynamics_person_key,
            "source_identity": self.source_identity,
            "birth_year": self.birth_year,
            "sex": self.sex,
            "status": self.status,
            "reasons": list(self.reasons),
            "gaps": {
                name: year_ranges(years) for name, years in self.gaps.items()
            },
            "result": None if self.result is None else self.result.document(),
        }


def run_cohort(
    history: ClosedCohortEarningsHistory,
    *,
    entitlement_age: int,
    declaration: ProjectedAmountDeclaration | None,
    wage_index: AnnualSeries,
    binding: AxiomEngineBinding,
    contribution_base: AnnualSeries | None = None,
    pre_projection: Mapping[int, CallerSuppliedHistory] | None = None,
    runner: Runner | None = None,
) -> tuple[PersonOutcome, ...]:
    """Run every original cohort member; refusals never stop the others.

    A changed or absent bound file raises :class:`BindingMismatch` and stops
    the whole run.
    """
    demographics = cohort_demographics(history)
    outcomes = []
    for person in history.histories:
        key = person.roster_keys[0]
        demographic = demographics.get(key)
        common = {
            "dynamics_person_key": key,
            "source_identity": _source_identity(history, key),
            "birth_year": (
                None if demographic is None else demographic.birth_year
            ),
            "sex": None if demographic is None else demographic.sex,
        }
        try:
            prepared = prepare_cohort_person(
                history,
                key,
                demographics=demographics,
                entitlement_age=entitlement_age,
                declaration=declaration,
                wage_index=wage_index,
                contribution_base=contribution_base,
                pre_projection=(pre_projection or {}).get(key),
            )
            result = execute_request(prepared, binding, runner=runner)
        except BenefitBridgeRefusal as refusal:
            outcomes.append(
                PersonOutcome(
                    **common,
                    status="refused",
                    reasons=refusal.reasons,
                    gaps=refusal.gaps,
                )
            )
        except AxiomExecutionError as error:
            outcomes.append(
                PersonOutcome(**common, status="failed", reasons=(str(error),))
            )
        else:
            outcomes.append(
                PersonOutcome(**common, status="executed", result=result)
            )
    return tuple(outcomes)
