"""Cited OASDI coverage law, by income year, for CE1 (1968–2026).

This opt-in registry supplies legal rules to CE3; it classifies no survey
record. Dates describe service/income years, never interview years. A rule's
conditions and statutory units remain available as source-backed parameters.
CE2 has not supplied identification evidence: ``awaiting_ce2`` is not
``identified``. The two readings of rare exclusions remain separate options.

Invariants (property tests in ``tests/income_resources``):

* Every family/year lookup returns rules or raises a typed refusal, never an
  empty result. A service-year lookup checks every day, preserving midyear
  changes. A family whose rows set ``parameters.effective_basis`` to
  ``taxable_year_start`` uses the beginning of the taxable year: year-only
  lookup assumes January 1, while ``lookup_date`` accepts the actual start.
  Every row of one family must use the same date axis.
* Effective ranges partition each family's support. Unexplained overlaps
  are invalid; named alternatives require an explicit selection at lookup.
  Gaps and explicitly open legal questions refuse the affected query.
* Each row states its residual default, equal to its top-level consequence.
  Cases carry a row-unique ``case_id``, an integer ``precedence``, nonempty
  trigger-fact conditions and an enum consequence. Precedence is first match
  wins: a row's precedence values are exactly 1..n, the matching case with
  the smallest value decides, and the residual applies only when no case
  matches (``CoverageRule.resolve``). A case's ``overrides`` names the cases
  it displaces by statute, such as an exclusion an exception lifts; each
  must rank below it and carry a different consequence. Cases are stored in
  precedence order, so input order never changes resolution. CE3 never
  classifies from the top-level consequence alone. ``open`` also represents
  missing facts.
* Cases are ranked rather than required to be mutually exclusive because
  the statutes are drafted as exclusions, exceptions to them and exceptions
  to those exceptions (42 U.S.C. 410(a)(5)(B) with (C)–(H), and Pub. L.
  98-369 section 2601(d)). Mutually exclusive cases would repeat the
  negation of every higher-ranked condition in free text that no loader can
  check; ranks and override references are checked here.
* Open legal rows have null/``open`` consequences, named alternatives and
  no chosen reading. They refuse even if a caller selects an alternative.
* Each rule cites a capture; loading checks every citation's SHA-256 against
  a file inside the capture directory, including nested example/bound cites.
* Trigger facts belong to FIELD_PURPOSES or the listed CE1 extensions.
* ``awaiting_ce2`` never establishes identification.
* A negligible candidate requires a cited prevalence bound and population;
  a missing bound preserves strict unresolved treatment and search history.
* A threshold declared monotone cannot decline across its published years.
  Only the optional-method limits carry this flag: their quarter-of-coverage
  inputs follow the statutory prior-year floor in 42 U.S.C. 413(d)(2).
  Constant series carry no claim of a statutory nondecrease requirement.
  The indexed domestic/election laws use their specified rounding and floors;
  future computation requires named index inputs, never an extrapolation.
* Row order does not affect validation, lookup or canonical JSON round trips.
* Worked examples carry an oracle label and nonempty inputs and outcomes.
  Conformance tests consume every published field and check the outcome.

Threshold amounts use the record's unit (dollars unless stated as days).
Aggregation scopes identify the statutory unit: ``component`` is one payment;
``employer_employee_year``, ``employer_employee_quarter``,
``employer_employee_month``, ``employer_employee_day`` and
``employer_employee_trip`` aggregate one employer-worker relationship over
that period or trip. ``employer_year`` aggregates the employer's payroll;
``person_year`` and ``person_month`` aggregate one person's eligible amounts;
``calendar_quarter`` and ``calendar_month`` aggregate all eligible amounts
within that period only where the law actually specifies that broader unit.
Each record retains its lower- or upper-bound comparison and aggregation.
Threshold computation returns exact Fractions. No classification, tax cap or
empirical prior is implemented here. Published examples test source-backed
conditions and amounts against legal lookup results.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
from types import MappingProxyType
from typing import Any

from populace_dynamics.data.historical_coverage_rule_validation import (
    FIELD_PURPOSES,
)

SCHEMA_VERSION = "coverage_rules.ce1.v3"
FIRST_INCOME_YEAR = 1968
LAST_INCOME_YEAR = 2026
CAPTURE_DIRECTORY = (
    Path(__file__).resolve().parents[3]
    / "data/external/snapshots/income_resources_ce1_v1"
)
REGISTRY_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/external/income_resources_ce1/coverage_rules.json"
)

# Legal facts absent from the retired campaign's broad field-purpose list.
CE1_FIELD_PURPOSES = (
    "age",
    "citizenship",
    "place_of_work",
    "active_us_military_service",
    "remuneration_in_self_employment",
    "retirement_payment",
    "employer_tax_exempt_status",
    "church_employer_election",
    "religious_vow_of_poverty",
    "federal_hire_date",
    "continuous_federal_service",
    "cash_remuneration",
    "employer_annual_payroll",
    "days_of_agricultural_work",
    "family_relationship",
    "visa_status",
    "benefit_entitlement_date",
    "services_performed_date",
    "copyright_or_patent_date",
    "copyright_or_patent_personal_effort",
    "royalties",
    "self_employment_optional_method_election",
    "trade_or_business",
    "partnership_status",
    "material_participation",
    "conservation_reserve_payment",
    "public_office_fee_basis",
    "insurance_sales_termination_payment",
    "nonprofit_organization",
    "nonprofit_coverage_waiver",
    "nonprofit_employee_concurrence",
    "agricultural_share_arrangement",
    "communist_organization_registration",
    "fishing_catch_share_arrangement",
    "fishing_crew_size",
    "fishing_additional_cash_conditions",
    "historical_fica_treatment",
    "newspaper_service_arrangement",
    "direct_seller_contract",
    "tribal_council_service",
    "tribal_federal_recognition",
    "tribal_coverage_agreement",
    "historical_earnings_posting",
    "country_of_residence",
    "american_employer",
    "congregation_predominantly_us_citizens",
    "community_property_income",
    "business_operator_spouse",
    "joint_business_distributive_shares",
    "substantially_all_business_management_and_control",
    "agent_or_employee_participation",
    "rental_arrangement_requires_material_participation",
    "rental_income",
    "real_estate_dealer_status",
    "services_to_occupants",
    "dividend_or_interest_income",
    "securities_dealer_status",
    "property_disposition_type",
    "net_operating_loss_deduction",
    "residence_period",
    "foreign_earned_income_exclusion",
    "possession_income_exclusion",
    "tribal_fishing_rights_income",
    "tribal_fishing_qualified_entity",
    "health_insurance_deduction",
    "partner_death_date",
    "partnership_taxable_year",
    "taxable_year",
    "taxable_year_start",
    "clergy_retirement_benefit",
    "benefit_type",
    "early_retirement_age_year",
    # Fee-based public office: irrevocable 1968 election.
    "public_office_1968_exemption_election",
    # Treaty fishing: membership and member-performed activity share.
    "tribal_membership",
    "tribal_fishing_member_activity",
    # Spousal venture election and joint-return conditions under 761(f).
    "qualified_joint_venture_election",
    "joint_return",
    # Retired-partner payments: services, obligations and capital conditions.
    "partner_no_services",
    "partner_no_other_obligation",
    "partner_capital_paid",
    # Noncash agricultural transfers: control and economic cash equivalence.
    "noncash_transfer_cash_equivalence",
    "noncash_transfer_dominion_control",
)
TRIGGER_FACTS = frozenset((*FIELD_PURPOSES, *CE1_FIELD_PURPOSES))
CONSEQUENCES = frozenset(
    {"covered", "noncovered", "covered_above_threshold", "open"}
)
CASE_FIELDS = frozenset(
    {
        "case_id",
        "precedence",
        "when",
        "consequence",
        "description",
        "overrides",
    }
)
REQUIRED_CASE_FIELDS = frozenset(
    {"case_id", "precedence", "when", "consequence"}
)


class CoverageRegistryError(ValueError):
    """Base for malformed evidence or a refused legal lookup."""


class RegistryValidationError(CoverageRegistryError):
    """The registry does not meet the CE1 schema."""


class CaptureIntegrityError(CoverageRegistryError):
    """A citation is missing, unsafe, or differs from its pinned capture."""


class NoRuleError(CoverageRegistryError):
    """No rule is recorded for the requested family or income year."""


class RuleGapError(NoRuleError):
    """At least one date in the requested interval has no legal rule."""


class RuleOverlapError(RegistryValidationError):
    """Overlapping effective ranges lack distinct named alternatives."""


class AlternativeRequiredError(CoverageRegistryError):
    """The source question has named options and no selected reading."""


class OpenRuleError(CoverageRegistryError):
    """The requested law is explicitly open or its source is blocked."""


class ThresholdUnavailableError(CoverageRegistryError):
    """Neither a published threshold nor all named index inputs exist."""


class TableDefinitionUnverifiedError(CoverageRegistryError):
    """CE5 cannot use an unverified table-membership definition."""


class SourceTextUnavailableError(CoverageRegistryError):
    """A binary source needs a pinned text derivative for passage checks."""


class UnknownIdentifierError(LookupError):
    """The caller named an identifier this registry does not define.

    A typo is a caller error, not a legal refusal, so this class sits
    outside ``CoverageRegistryError``.
    """


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(value[key]) for key in sorted(value)}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _has_chosen_reading(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(
            {
                "chosen_reading",
                "selected_reading",
                "operative_current_text",
            }.intersection(value)
        ) or any(_has_chosen_reading(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_chosen_reading(child) for child in value)
    return False


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryValidationError(message)


def _text(value: Any, name: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), name)
    return value


def _date(value: Any) -> date:
    try:
        _require(isinstance(value, str), "date must be ISO text")
        parsed = date.fromisoformat(value)
        _require(parsed.isoformat() == value, "date must be YYYY-MM-DD")
        return parsed
    except (ValueError, TypeError) as exc:
        raise RegistryValidationError(f"invalid date: {value!r}") from exc


def _year(value: Any) -> int:
    if type(value) is not int:
        raise TypeError("income year must be an integer")
    if not FIRST_INCOME_YEAR <= value <= LAST_INCOME_YEAR:
        raise NoRuleError(f"income year outside 1968–2026: {value!r}")
    return value


def _validated_cases(
    raw: Any, facts: set[str]
) -> tuple[Mapping[str, Any], ...]:
    """Check case fields and first-match ranks; return precedence order."""
    _require(isinstance(raw, (list, tuple)), "cases list")
    by_id: dict[str, Mapping[str, Any]] = {}
    for case in raw:
        _require(isinstance(case, Mapping), "case object")
        _require(
            REQUIRED_CASE_FIELDS <= set(case) <= CASE_FIELDS, "case fields"
        )
        case_id = _text(case["case_id"], "case_id")
        _require(
            re.fullmatch(r"[a-z0-9][a-z0-9_]*", case_id) is not None,
            "case_id must be a lowercase identifier",
        )
        _require(case_id not in by_id, "duplicate case_id")
        _require(
            type(case["precedence"]) is int, "case precedence must be int"
        )
        when = case["when"]
        _require(
            isinstance(when, Mapping) and bool(when),
            "case conditions must be a nonempty object",
        )
        _require(set(when) <= facts, "case uses undeclared trigger fact")
        for condition in when.values():
            _require(
                isinstance(condition, bool)
                or (isinstance(condition, str) and bool(condition.strip())),
                "case condition must be nonempty text or a boolean",
            )
        _require(case["consequence"] in CONSEQUENCES, "case consequence")
        if "description" in case:
            _text(case["description"], "case description")
        by_id[case_id] = case
    ranks = sorted(case["precedence"] for case in by_id.values())
    _require(
        ranks == list(range(1, len(ranks) + 1)),
        "case precedence must run exactly 1..n",
    )
    for case in by_id.values():
        if "overrides" not in case:
            continue
        targets = case["overrides"]
        _require(
            isinstance(targets, (list, tuple))
            and bool(targets)
            and all(isinstance(t, str) for t in targets)
            and len(set(targets)) == len(targets),
            "case overrides must list distinct case IDs",
        )
        for target in targets:
            _require(target in by_id, "case overrides an unknown case_id")
            _require(
                by_id[target]["precedence"] > case["precedence"],
                "an overriding case must precede the case it overrides",
            )
            _require(
                by_id[target]["consequence"] != case["consequence"],
                "a case override must change the consequence",
            )
    return tuple(
        _freeze(case)
        for case in sorted(by_id.values(), key=lambda c: c["precedence"])
    )


@dataclass(frozen=True)
class Citation:
    """One pinpoint reference to bytes stored in CE1's capture directory."""

    capture: str
    sha256: str
    authority: str
    location: str
    quote: str | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> Citation:
        _require(isinstance(raw, Mapping), "citation must be an object")
        _require(
            set(raw)
            <= {"capture", "sha256", "authority", "location", "quote"},
            "unknown citation field",
        )
        try:
            result = cls(**raw)
        except TypeError as exc:
            raise RegistryValidationError("incomplete citation") from exc
        for name in ("capture", "sha256", "authority", "location"):
            _text(getattr(result, name), f"citation.{name}")
        _require(
            re.fullmatch(r"[0-9a-f]{64}", result.sha256) is not None,
            "citation SHA-256 must have 64 lowercase hex digits",
        )
        if result.quote is not None:
            _text(result.quote, "citation.quote")
        return result

    def to_dict(self) -> dict[str, Any]:
        result = dict(
            capture=self.capture,
            sha256=self.sha256,
            authority=self.authority,
            location=self.location,
        )
        if self.quote is not None:
            result["quote"] = self.quote
        return result


@dataclass(frozen=True)
class CoverageRule:
    """One regime with explicit conditional cases and a residual default."""

    rule_id: str
    family: str
    effective_start: date
    effective_end: date
    citations: tuple[Citation, ...]
    trigger_facts: tuple[str, ...]
    consequence: str | None
    residual_default: Mapping[str, Any]
    cases: tuple[Mapping[str, Any], ...]
    open_alternatives: tuple[Mapping[str, str], ...]
    identification_class: str
    description: str
    parameters: Mapping[str, Any]
    worked_examples: tuple[Mapping[str, Any], ...]
    rare_exclusion: Mapping[str, Any] | None
    alternative: Mapping[str, str] | None
    open_reason: str | None

    @property
    def is_identified(self) -> bool:
        """Only CE2's explicit identified value can establish this class."""
        return self.identification_class == "identified"

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CoverageRule:
        _require(isinstance(raw, Mapping), "rule must be an object")
        names = set(cls.__dataclass_fields__)
        _require(set(raw) == names, f"rule fields differ: {set(raw) ^ names}")
        for name in ("rule_id", "family", "description"):
            _text(raw[name], name)
        start, end = _date(raw["effective_start"]), _date(raw["effective_end"])
        _require(start <= end, "effective range is reversed")
        _require(
            isinstance(raw["citations"], (list, tuple))
            and bool(raw["citations"]),
            "every rule needs at least one citation",
        )
        citations = tuple(Citation.from_dict(c) for c in raw["citations"])
        facts = raw["trigger_facts"]
        _require(
            isinstance(facts, (list, tuple))
            and bool(facts)
            and all(isinstance(f, str) for f in facts),
            "trigger facts must be a nonempty list of names",
        )
        _require(len(facts) == len(set(facts)), "duplicate trigger fact")
        _require(set(facts) <= TRIGGER_FACTS, "unknown trigger fact")
        consequence = raw["consequence"]
        _require(
            consequence is None or consequence in CONSEQUENCES,
            "unknown consequence",
        )
        residual = raw["residual_default"]
        _require(isinstance(residual, Mapping), "residual default object")
        _require(
            set(residual) == {"consequence", "description"},
            "residual default fields",
        )
        _require(
            residual["consequence"] == consequence,
            "residual default must equal top-level consequence",
        )
        _text(residual["description"], "residual default description")
        cases = _validated_cases(raw["cases"], set(facts))
        alternatives = raw["open_alternatives"]
        _require(
            isinstance(alternatives, (list, tuple)), "open alternatives list"
        )
        for option in alternatives:
            _require(
                isinstance(option, Mapping)
                and set(option) == {"name", "description"},
                "open alternative fields",
            )
            _text(option["name"], "open alternative name")
            _text(option["description"], "open alternative description")
        _require(
            len({o["name"] for o in alternatives}) == len(alternatives),
            "duplicate open alternative name",
        )
        if raw["open_reason"] is not None:
            _require(
                consequence in {None, "open"},
                "open row has chosen consequence",
            )
            _require(
                len(alternatives) >= 2, "open row needs named alternatives"
            )
        else:
            _require(
                consequence is not None, "null consequence needs open reason"
            )
            _require(not alternatives, "closed row has open alternatives")
        _require(
            raw["identification_class"]
            in {"awaiting_ce2", "identified", "prior", "unidentified"},
            "unknown identification class",
        )
        _require(isinstance(raw["parameters"], Mapping), "parameters object")
        _require(
            "cases" not in raw["parameters"], "cases belong in the schema"
        )
        if raw["parameters"].get("effective_basis") == "taxable_year_start":
            _require(
                "taxable_year_start" in facts,
                "taxable-year axis needs taxable_year_start trigger fact",
            )
        if raw["open_reason"] is not None:
            _require(
                not _has_chosen_reading(raw["parameters"]),
                "open row has chosen reading",
            )
        _require(
            isinstance(raw["worked_examples"], (list, tuple)),
            "worked_examples list",
        )
        examples = []
        for example in raw["worked_examples"]:
            _require(isinstance(example, Mapping), "example object")
            for name in (
                "example_id",
                "source_passage",
                "expected_rule_id",
                "calculation",
            ):
                _text(example.get(name), f"example.{name}")
            _year(example.get("income_year"))
            Citation.from_dict(example.get("citation"))
            for name in ("published_inputs", "published_outputs"):
                _require(
                    isinstance(example.get(name), Mapping)
                    and bool(example[name]),
                    f"example.{name} nonempty object",
                )
            _require(
                "expected_parameters" not in example,
                "examples must test outcomes rather than repeated parameters",
            )
            examples.append(_freeze(example))
        rare = raw["rare_exclusion"]
        if rare is not None:
            _require(isinstance(rare, Mapping), "rare_exclusion object")
            _require(rare.get("strict") == "unresolved", "strict reading")
            _require("negligible_candidate" in rare, "missing rare reading")
            _require(
                isinstance(rare.get("searches"), (list, tuple)),
                "rare-exclusion searches must be recorded",
            )
            candidate = rare["negligible_candidate"]
            if candidate is not None:
                _require(isinstance(candidate, Mapping), "bound object")
                _text(candidate.get("population"), "bound.population")
                _text(candidate.get("bound"), "bound.bound")
                Citation.from_dict(candidate.get("citation"))
            else:
                _require(
                    bool(rare["searches"])
                    and all(
                        (isinstance(s, str) and s.strip())
                        or (
                            isinstance(s, Mapping)
                            and isinstance(s.get("query"), str)
                            and s["query"].strip()
                        )
                        for s in rare["searches"]
                    ),
                    "a null prevalence bound requires recorded searches",
                )
        alternative = raw["alternative"]
        if alternative is not None:
            _require(isinstance(alternative, Mapping), "alternative object")
            for name in ("group", "name", "explanation"):
                _text(alternative.get(name), f"alternative.{name}")
        if raw["open_reason"] is not None:
            _text(raw["open_reason"], "open_reason")
        return cls(
            rule_id=raw["rule_id"],
            family=raw["family"],
            effective_start=start,
            effective_end=end,
            citations=tuple(
                sorted(citations, key=lambda c: (c.capture, c.location))
            ),
            trigger_facts=tuple(sorted(facts)),
            consequence=consequence,
            residual_default=_freeze(residual),
            cases=cases,
            open_alternatives=tuple(_freeze(o) for o in alternatives),
            identification_class=raw["identification_class"],
            description=raw["description"],
            parameters=_freeze(raw["parameters"]),
            worked_examples=tuple(
                sorted(examples, key=lambda e: e["example_id"])
            ),
            rare_exclusion=_freeze(rare),
            alternative=_freeze(alternative),
            open_reason=raw["open_reason"],
        )

    def resolve(self, matching_case_ids: Iterable[str]) -> Mapping[str, Any]:
        """Apply first-match precedence to the cases whose conditions hold.

        ``matching_case_ids`` names every case whose ``when`` conditions the
        caller found true. Return the matching case with the smallest
        precedence, or the residual default when none matches. An unknown
        case ID is a caller error; an open row refuses.
        """
        if isinstance(matching_case_ids, (str, bytes)) or not isinstance(
            matching_case_ids, Iterable
        ):
            raise TypeError("matching_case_ids must be an iterable of IDs")
        matched = set(matching_case_ids)
        if not all(isinstance(case_id, str) for case_id in matched):
            raise TypeError("case IDs must be strings")
        unknown = matched - {case["case_id"] for case in self.cases}
        if unknown:
            raise UnknownIdentifierError(
                f"{self.rule_id}: unknown case IDs {sorted(unknown)}"
            )
        if self.open_reason is not None:
            raise OpenRuleError(f"{self.rule_id}: {self.open_reason}")
        for case in self.cases:
            if case["case_id"] in matched:
                return case
        return self.residual_default

    def to_dict(self) -> dict[str, Any]:
        result = {
            name: _plain(getattr(self, name))
            for name in self.__dataclass_fields__
        }
        result["effective_start"] = self.effective_start.isoformat()
        result["effective_end"] = self.effective_end.isoformat()
        result["citations"] = [c.to_dict() for c in self.citations]
        return result


class _CaptureText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)


def source_text(path: Path) -> str:
    """Normalize HTML/UTF-8 text; binary sources need pinned derivatives."""
    if path.suffix.lower() == ".pdf":
        raise SourceTextUnavailableError(
            "pin a text derivative linked to the PDF before checking a passage"
        )
    parser = _CaptureText()
    try:
        parser.feed(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise SourceTextUnavailableError(
            f"source text unavailable: {path.name}"
        ) from exc
    return " ".join(" ".join(parser.parts).split())


def _verify_citations(
    value: Any, root: Path, verified: dict[Path, str] | None = None
) -> None:
    # Hash a capture once per load; never retain a cache across registry loads.
    # Every citation still compares its own expected digest with those bytes.
    if verified is None:
        verified = {}
    if isinstance(value, Mapping):
        if "capture" in value:
            citation = Citation.from_dict(value)
            relative = Path(citation.capture)
            path = (root / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(
                root.resolve()
            ):
                raise CaptureIntegrityError(
                    "citation escapes capture directory"
                )
            try:
                if path not in verified:
                    verified[path] = hashlib.sha256(
                        path.read_bytes()
                    ).hexdigest()
                digest = verified[path]
            except OSError as exc:
                raise CaptureIntegrityError(
                    f"missing capture: {citation.capture}"
                ) from exc
            if digest != citation.sha256:
                raise CaptureIntegrityError(
                    f"capture hash mismatch: {citation.capture}"
                )
        for child in value.values():
            _verify_citations(child, root, verified)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _verify_citations(child, root, verified)


def _fraction(value: Any, *, caller: bool = False) -> Fraction:
    try:
        if isinstance(value, bool) or isinstance(value, float):
            raise TypeError("use an integer or exact decimal string")
        result = Fraction(value)
        if result < 0:
            raise ValueError("threshold/index must be nonnegative")
        return result
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        if caller:
            if isinstance(exc, TypeError):
                raise TypeError("invalid exact index input") from exc
            raise ValueError("invalid exact index input") from exc
        raise RegistryValidationError("invalid exact threshold/index") from exc


@dataclass(frozen=True)
class CoverageRegistry:
    """Validated rules plus cited thresholds and downstream definitions."""

    rules: tuple[CoverageRule, ...]
    thresholds: tuple[Mapping[str, Any], ...]
    metadata: Mapping[str, Any]

    @property
    def families(self) -> tuple[str, ...]:
        return tuple(sorted({r.family for r in self.rules}))

    @classmethod
    def from_dict(
        cls, raw: Mapping[str, Any], *, capture_root: Path
    ) -> CoverageRegistry:
        _require(isinstance(raw, Mapping), "registry must be an object")
        _require(raw.get("schema_version") == SCHEMA_VERSION, "schema version")
        _require(
            raw.get("income_years") == [1968, 2026], "income-year support"
        )
        _require(isinstance(raw.get("rules"), list), "rules list")
        _require(bool(raw["rules"]), "registry must contain a rule")
        rules = tuple(
            sorted(
                (CoverageRule.from_dict(r) for r in raw["rules"]),
                key=lambda r: (r.family, r.effective_start, r.rule_id),
            )
        )
        _require(len({r.rule_id for r in rules}) == len(rules), "duplicate ID")
        for family in {r.family for r in rules}:
            axes = {
                r.parameters.get("effective_basis") == "taxable_year_start"
                for r in rules
                if r.family == family
            }
            _require(
                len(axes) == 1, "family mixes service and taxable-year axes"
            )
        for i, left in enumerate(rules):
            for right in rules[i + 1 :]:
                if left.family != right.family:
                    break
                if right.effective_start > left.effective_end:
                    break
                a, b = left.alternative, right.alternative
                if not (
                    a
                    and b
                    and a["group"] == b["group"]
                    and a["name"] != b["name"]
                ):
                    raise RuleOverlapError(
                        f"unexplained overlap: {left.rule_id}, {right.rule_id}"
                    )
        thresholds = raw.get("thresholds", [])
        _require(isinstance(thresholds, list), "thresholds list")
        ids = []
        for threshold in thresholds:
            _require(isinstance(threshold, Mapping), "threshold object")
            ids.append(_text(threshold.get("threshold_id"), "threshold_id"))
            _require(
                threshold.get("aggregation_scope")
                in {
                    "component",
                    "employer_employee_year",
                    "person_year",
                    "employer_year",
                    "calendar_quarter",
                    "employer_employee_quarter",
                    "employer_employee_day",
                    "person_month",
                    "calendar_month",
                    "employer_employee_month",
                    "employer_employee_trip",
                },
                "threshold aggregation scope",
            )
            _text(threshold.get("eligible_concept"), "eligible concept")
            _require(
                threshold.get("comparison")
                in {"at_least", "greater_than", "at_most"},
                "threshold comparison",
            )
            _require(bool(threshold.get("citations")), "threshold citations")
            for c in threshold["citations"]:
                Citation.from_dict(c)
            values = threshold.get("published_values")
            _require(isinstance(values, Mapping), "published_values object")
            previous = None
            for year, amount in sorted(values.items()):
                try:
                    canonical_year = str(_year(int(year)))
                except (ValueError, TypeError) as exc:
                    raise RegistryValidationError(
                        "invalid threshold year"
                    ) from exc
                _require(canonical_year == year, "threshold year")
                amount = _fraction(amount)
                if threshold.get("monotone") and previous is not None:
                    _require(amount >= previous, "monotone threshold fell")
                previous = amount
            index = threshold.get("indexing")
            if index is not None:
                _require(isinstance(index, Mapping), "indexing object")
                _require(
                    index.get("kind") in {"awi", "quarter_of_coverage_sum"},
                    "unsupported index",
                )
                _require(
                    type(index.get("first_year")) is int
                    and type(index.get("last_year")) is int
                    and index["first_year"] <= index["last_year"],
                    "index support years",
                )
                if index["kind"] == "quarter_of_coverage_sum":
                    _text(index.get("parameter_name"), "quarter input name")
                    for name in (
                        "multiplier_numerator",
                        "multiplier_denominator",
                    ):
                        _require(
                            type(index.get(name)) is int and index[name] > 0,
                            "positive quarter multiplier",
                        )
                    continue
                _require(_fraction(index.get("base_amount")) > 0, "index base")
                _require(
                    _fraction(index.get("round_to")) > 0, "index rounding"
                )
                _require(
                    index.get("rounding") in {"nearest", "floor"}, "rounding"
                )
                _require(
                    index.get("floor") in {None, "prior_year"}, "index floor"
                )
                _require(type(index.get("lag_years")) is int, "index lag")
                _require(index["lag_years"] >= 0, "negative index lag")
                _require(
                    type(index.get("first_year")) is int
                    and type(index.get("last_year")) is int
                    and index["first_year"] <= index["last_year"],
                    "index support years",
                )
                if index.get("base_index") is not None:
                    _require(_fraction(index["base_index"]) > 0, "index base")
                else:
                    _require(
                        type(index.get("base_index_year")) is int,
                        "named base index year required",
                    )
        _require(len(ids) == len(set(ids)), "duplicate threshold ID")
        definitions = raw.get("table_definitions", [])
        _require(isinstance(definitions, list), "table definitions list")
        definition_ids = []
        for definition in definitions:
            _require(
                isinstance(definition, Mapping), "table definition object"
            )
            definition_ids.append(
                _text(definition.get("definition_id"), "table definition ID")
            )
            _require(
                definition.get("status")
                in ("verified", "TABLE_DEFINITION_UNVERIFIED"),
                "table definition status",
            )
            if definition["status"] == "verified":
                _text(
                    definition.get("source_definition"),
                    "table source definition",
                )
                evidence = definition.get("citations")
                _require(
                    isinstance(evidence, list) and bool(evidence),
                    "table citations",
                )
                citations = [Citation.from_dict(c) for c in evidence]
                _require(
                    any(c.quote for c in citations),
                    "verified table definition needs a quoted source passage",
                )
            else:
                _text(definition.get("reason"), "unverified table reason")
                evidence = definition.get("citations", [])
                _require(isinstance(evidence, list), "table citations")
                for citation in evidence:
                    Citation.from_dict(citation)
        _require(
            len(definition_ids) == len(set(definition_ids)),
            "duplicate table definition ID",
        )
        ret = raw.get("earnings_test")
        if ret is not None:
            _require(isinstance(ret, Mapping), "RET concept object")
            if ret.get("status") == "verified":
                _require(bool(ret.get("citations")), "RET citations")
                for citation in ret["citations"]:
                    Citation.from_dict(citation)
                support = ret.get("verified_income_years")
                _require(
                    isinstance(support, list) and bool(support),
                    "verified RET income years required",
                )
                for year in support:
                    _year(year)
        _verify_citations(raw, capture_root)
        return cls(
            rules=rules,
            thresholds=tuple(
                _freeze(t)
                for t in sorted(thresholds, key=lambda t: t["threshold_id"])
            ),
            metadata=_freeze(
                {
                    k: v
                    for k, v in raw.items()
                    if k not in {"rules", "thresholds"}
                }
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **_plain(self.metadata),
            "rules": [r.to_dict() for r in self.rules],
            "thresholds": _plain(self.thresholds),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    def _lookup_interval(
        self, family: str, start: date, end: date, alternative: str | None
    ) -> tuple[CoverageRule, ...]:
        candidates = [
            r
            for r in self.rules
            if r.family == family
            and r.effective_start <= end
            and r.effective_end >= start
        ]
        if not candidates:
            family_rules = [r for r in self.rules if r.family == family]
            if family_rules and (
                min(r.effective_start for r in family_rules)
                <= start
                <= max(r.effective_end for r in family_rules)
            ):
                raise RuleGapError(f"rule gap: {family}, {start}–{end}")
            raise NoRuleError(f"no rule: {family}, {start}–{end}")
        # Sweep inclusive ranges using their next-day endpoints.
        boundaries = {start, end + timedelta(days=1)}
        for r in candidates:
            boundaries.add(max(start, r.effective_start))
            boundaries.add(min(end, r.effective_end) + timedelta(days=1))
        selected: dict[str, CoverageRule] = {}
        for point in sorted(boundaries)[:-1]:
            active = [
                r
                for r in candidates
                if r.effective_start <= point <= r.effective_end
            ]
            if not active:
                raise RuleGapError(f"rule gap: {family}, {point}")
            if any(r.alternative for r in active):
                names = sorted(r.alternative["name"] for r in active)
                if alternative is None:
                    raise AlternativeRequiredError(
                        f"{family}, {point}: select one of {names}"
                    )
                active = [
                    r for r in active if r.alternative["name"] == alternative
                ]
                if not active:
                    raise RuleGapError(
                        f"{family}, {point}: no rule for selected alternative {alternative}"
                    )
            for r in active:
                if r.open_reason:
                    raise OpenRuleError(f"{r.rule_id}: {r.open_reason}")
                selected[r.rule_id] = r
        return tuple(
            sorted(
                selected.values(), key=lambda r: (r.effective_start, r.rule_id)
            )
        )

    def lookup(
        self, family: str, income_year: int, *, alternative: str | None = None
    ) -> tuple[CoverageRule, ...]:
        """Return regimes and cases on the family's stated date axis.

        Service years check every date. Taxable-year families assume January
        1; use lookup_date for a fiscal year's actual start.
        Conditions remain declarative: consumers evaluate every case from its
        trigger facts, then pass the matching case IDs to
        ``CoverageRule.resolve``, which applies the first match in
        precedence order or the residual when none matches.
        """
        year = _year(income_year)
        start = date(year, 1, 1)
        taxable_year_axis = any(
            r.family == family
            and r.parameters.get("effective_basis") == "taxable_year_start"
            for r in self.rules
        )
        end = start if taxable_year_axis else date(year, 12, 31)
        return self._lookup_interval(family, start, end, alternative)

    def lookup_date(
        self,
        family: str,
        service_date: date,
        *,
        alternative: str | None = None,
    ) -> tuple[CoverageRule, ...]:
        """Resolve a service date or an actual taxable-year start.

        ``parameters.effective_basis == "taxable_year_start"`` makes the
        date the beginning of that taxable year, including fiscal years.
        """
        if type(service_date) is not date:
            raise TypeError("service_date must be a date")
        _year(service_date.year)
        return self._lookup_interval(
            family, service_date, service_date, alternative
        )

    def threshold(
        self,
        threshold_id: str,
        income_year: int,
        *,
        index_inputs: Mapping[str, Any] | None = None,
    ) -> Fraction:
        """Published dollars, or statute-indexed dollars with named inputs.

        Inputs use ``national_average_wage_index_YYYY`` and, when a floor's
        preceding value is unpublished, ``prior_year_threshold_YYYY``.
        A supplied base index must be positive. Ties round up for ``nearest``.
        """
        year = _year(income_year)
        matches = [
            t for t in self.thresholds if t["threshold_id"] == threshold_id
        ]
        if not matches:
            raise ThresholdUnavailableError(
                f"unknown threshold: {threshold_id}"
            )
        threshold = matches[0]
        values = threshold["published_values"]
        if str(year) in values:
            return _fraction(values[str(year)])
        index = threshold.get("indexing")
        if not index or not index["first_year"] <= year <= index["last_year"]:
            raise ThresholdUnavailableError(
                f"unpublished: {threshold_id}, {year}"
            )
        if index_inputs is not None and not isinstance(index_inputs, Mapping):
            raise TypeError("index_inputs must be a mapping")
        supplied = index_inputs or {}

        def need(name: str) -> Fraction:
            if name not in supplied:
                raise ThresholdUnavailableError(f"missing named input: {name}")
            return _fraction(supplied[name], caller=True)

        if index["kind"] == "quarter_of_coverage_sum":
            name = index["parameter_name"]
            if name not in supplied:
                raise ThresholdUnavailableError(f"missing named input: {name}")
            quarters = supplied[name]
            if not isinstance(quarters, (list, tuple)) or len(quarters) != 4:
                raise ValueError("four named calendar-quarter inputs required")
            amount = (
                sum((_fraction(q, caller=True) for q in quarters), Fraction(0))
                / 100
            )
            amount *= Fraction(
                index["multiplier_numerator"], index["multiplier_denominator"]
            )
            earlier = [int(y) for y in values if int(y) < year]
            if threshold.get("monotone") and earlier:
                if amount < _fraction(values[str(max(earlier))]):
                    raise ValueError(
                        "supplied quarters violate the statutory nondecrease"
                    )
            return amount

        current = need(
            f"national_average_wage_index_{year - index['lag_years']}"
        )
        if index.get("base_index") is not None:
            base = _fraction(index["base_index"])
        else:
            base = need(
                f"national_average_wage_index_{index['base_index_year']}"
            )
        if base <= 0:
            raise ValueError("index denominator must be positive")
        multiple = _fraction(index["round_to"])
        raw = _fraction(index["base_amount"]) * current / base / multiple
        if index["rounding"] == "nearest":
            raw += Fraction(1, 2)
        rounded = (raw.numerator // raw.denominator) * multiple
        if index.get("floor") == "prior_year":
            previous_year = str(year - 1)
            previous = (
                _fraction(values[previous_year])
                if previous_year in values
                else need(f"prior_year_threshold_{year - 1}")
            )
            rounded = max(rounded, previous)
        return rounded

    def table_definition(self, definition_id: str) -> Mapping[str, Any]:
        """Return verified membership law; otherwise preserve CE5 absence."""
        for definition in self.metadata.get("table_definitions", ()):
            if definition["definition_id"] == definition_id:
                if definition["status"] != "verified":
                    raise TableDefinitionUnverifiedError(
                        f"TABLE_DEFINITION_UNVERIFIED: {definition_id}: "
                        f"{definition['reason']}"
                    )
                return definition
        raise TableDefinitionUnverifiedError(
            f"TABLE_DEFINITION_UNVERIFIED: {definition_id}: no definition"
        )

    def earnings_test_concept(self, income_year: int) -> Mapping[str, Any]:
        """Refuse to backcast current RET text across unverified history."""
        _year(income_year)
        concept = self.metadata.get("earnings_test", {})
        if concept.get("status") != "verified":
            raise OpenRuleError(
                concept.get("historical_refusal", "RET concept not verified")
            )
        if income_year not in concept["verified_income_years"]:
            raise OpenRuleError(
                f"RET history unverified for income year {income_year}"
            )
        return concept


def load_registry(
    path: Path | str = REGISTRY_PATH, *, capture_root: Path | None = None
) -> CoverageRegistry:
    """Load JSON and verify captures, kept separately for the CE1 registry.

    Custom registries default to adjacent captures; callers can supply an
    explicit capture directory without allowing citations to escape it.
    """
    path = Path(path)
    if capture_root is None:
        capture_root = (
            CAPTURE_DIRECTORY
            if path.resolve() == REGISTRY_PATH.resolve()
            else path.parent
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryValidationError(f"cannot load registry: {path}") from exc
    return CoverageRegistry.from_dict(raw, capture_root=capture_root)
