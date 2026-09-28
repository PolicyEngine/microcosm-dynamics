"""Frozen hypothetical application and ordering, a2-ratified-1 §§5.2–5.4."""

from dataclasses import dataclass

from populace_dynamics.ss.params import SSAParameters


class FilingRefusal(ValueError):
    """Unsupported filing facts; the whole attempt must stop at step 3."""

    def __init__(self, person_id, reason):
        self.person_id = person_id
        self.reason = reason
        super().__init__(f"person {person_id}: {reason}")


@dataclass(frozen=True)
class Application:
    year: int
    month: int
    case: str
    counters: dict[str, int]


@dataclass(frozen=True)
class Timing:
    year: int
    month: int
    months_early: int
    deferred: bool
    payable: bool


def application_month(
    *,
    birth_year,
    claim_year,
    entitlement_year,
    conversion_year,
    baseline_params: SSAParameters,
    opening_prior_claim=False,
    reference_year=2030,
    person_id=None,
) -> Application:
    """H reads baseline dates only; null claims select scheduled conversion."""
    if birth_year is None or entitlement_year is None:
        raise FilingRefusal(person_id, "missing birth or DI entitlement date")
    try:
        birth, award = int(birth_year), int(entitlement_year)
    except (ValueError, TypeError) as exc:
        raise FilingRefusal(
            person_id, "missing birth or DI entitlement date"
        ) from exc
    try:
        fra = baseline_params.fra_months(birth)
    except KeyError as exc:
        raise FilingRefusal(person_id, "missing baseline FRA bracket") from exc
    conversion = birth + (6 + fra) // 12
    counters = {}
    if claim_year is not None and claim_year < award:
        year, case = int(claim_year), "P"
        counter = (
            "s_prior_claim_opening"
            if opening_prior_claim
            else "s_prior_claim_projected"
        )
        counters[counter] = 1
    else:
        year, case = conversion, "Q"
        if claim_year is not None and not (
            int(claim_year) == conversion_year == conversion
        ):
            raise FilingRefusal(
                person_id, "claim/conversion/scheduled conversion disagree"
            )
    if year > reference_year:
        counters["s_application_after_reference"] = 1
    return Application(year, 12 * (year - birth), case, counters)


def spouse_timing(
    application: Application,
    *,
    birth_year: int,
    worker_entitlement_year: int,
    fra_months: int,
    worker_baseline_entitlement_year: int | None = None,
    worker_move_months: int = 0,
    reference_year: int = 2030,
) -> Timing:
    """Latest application/age-62/worker gate retains exact moved months."""
    worker_base = (
        worker_entitlement_year
        if worker_baseline_entitlement_year is None
        else worker_baseline_entitlement_year
    )
    year = max(application.year, birth_year + 62, worker_entitlement_year)
    month = max(
        application.month,
        744,
        12 * (worker_base - birth_year) + worker_move_months,
    )
    return Timing(
        year,
        month,
        max(0, fra_months - month),
        max(application.year, worker_entitlement_year) < birth_year + 62,
        year <= reference_year,
    )


def classify_ordering(
    application: Application,
    *,
    entitlement_year: int,
    di_entitlement_year: int,
    claim_year: int | None,
    recoveries: int = 0,
    person_id=None,
) -> str:
    """Unsupported spouse-first/ended-spell orderings never get Formula F."""
    if recoveries:
        raise FilingRefusal(
            person_id, "earlier DI spell ended before re-award"
        )
    if (
        application.case == "Q"
        and entitlement_year < di_entitlement_year
        or application.case == "P"
        and (claim_year is None or entitlement_year < claim_year)
    ):
        raise FilingRefusal(person_id, "spouse-only first is unsupported")
    if application.case == "Q":
        return (
            "concurrent"
            if entitlement_year == di_entitlement_year
            else "di_first"
        )
    return (
        "prior_rib_spouse_di"
        if entitlement_year < di_entitlement_year
        else "prior_rib_di_spouse"
    )
