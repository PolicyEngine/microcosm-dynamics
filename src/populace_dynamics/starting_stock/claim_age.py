"""A claim age for a retired worker whose file gives none.

The starting frame gives a retired worker's age and sex in the start
year, and no claim age. :func:`claim_age_posterior` weights each whole
claim age the person could have reached by the share of retired-worker
awards at that age in the year the person would have claimed, and
:func:`draw_claim_age` draws one from those weights with a uniform
keyed by seed and person id, so a person's draw never depends on who
else is drawn. :func:`single_year_age` draws a single year of age for a
person whose recorded age is a top code, by the same recipe.

What the draw ignores:

* **The month within the claim year.** A claim age is a whole year, and
  the claim is taken at the birthday month of that year, so a caller
  that needs months uses ``12 * claim_age``.
* **Disability conversions at full retirement age.** A disabled worker
  converted to a retired-worker benefit at full retirement age made no
  claiming choice; the draw treats every retired worker as having
  claimed, and the award shares it is given should leave conversions
  out (as ``claiming.claim_age_pmf`` does by default).
* **Any link between benefit level and claim age.** The posterior uses
  age, birth year and sex only. A person's benefit, and so their PIA,
  does not move the weights, whatever the true dependence of claim age
  on benefit level is.

The uniform. The key is the ASCII bytes of
``populace_dynamics.starting_stock.<draw>.v1|<seed>|<person_id>``, with
the seed and person id in decimal and ``<draw>`` either ``claim_age`` or
``single_year_age``. Its SHA-256 digest's first eight bytes, read as a
big-endian unsigned integer and divided by 2**64, give a uniform in
[0, 1). The draw walks the outcomes in rising order and returns the
first whose cumulative weight exceeds the uniform. If floating-point
summation leaves the last cumulative weight a hair under a uniform
close to 1, the draw returns the last outcome with positive weight.
"""

from __future__ import annotations

import hashlib
import math
import numbers
import operator
from collections.abc import Callable, Mapping

__all__ = [
    "CLAIM_AGE_KEY_PREFIX",
    "SINGLE_YEAR_AGE_KEY_PREFIX",
    "EARLIEST_CLAIM_AGE",
    "LATEST_CLAIM_AGE",
    "TOP_CODE_BANDS",
    "claim_age_posterior",
    "draw_claim_age",
    "single_year_age",
]

#: Key prefix of the claim-age uniform.
CLAIM_AGE_KEY_PREFIX = "populace_dynamics.starting_stock.claim_age.v1"
#: Key prefix of the single-year-of-age uniform.
SINGLE_YEAR_AGE_KEY_PREFIX = (
    "populace_dynamics.starting_stock.single_year_age.v1"
)

#: The whole claim ages a retired worker can have, as in
#: ``claiming.CLAIM_AGES``.
EARLIEST_CLAIM_AGE = 62
LATEST_CLAIM_AGE = 70

#: The file's two age top codes and the single years each stands for:
#: 80 stands for 80 to 84, and 85 for 85 and over (no upper end).
TOP_CODE_BANDS: dict[int, tuple[int, int | None]] = {
    80: (80, 84),
    85: (85, None),
}

_TWO_TO_THE_64 = 2**64

AwardShares = Callable[[str, int], Mapping[int, float]]
AgeShares = Callable[[int, str], Mapping[int, float]]


def _integer(label: str, value: object) -> int:
    """An integer, refusing booleans, floats and strings."""
    if isinstance(value, bool):
        raise TypeError(f"{label} must be an integer, not a bool")
    try:
        return operator.index(value)
    except TypeError as error:
        raise TypeError(f"{label} must be an integer") from error


def _weight(label: str, value: object) -> float:
    """A finite share of zero or more."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{label} must be a real number")
    out = float(value)
    if not math.isfinite(out) or out < 0.0:
        raise ValueError(f"{label} must be finite and not negative: {out!r}")
    return out


def _normalise(weights: dict[int, float], what: str) -> dict[int, float]:
    """Weights over rising outcomes, scaled to sum to one."""
    total = math.fsum(weights.values())
    if total <= 0.0:
        raise ValueError(f"every weight is zero for {what}")
    return {key: weights[key] / total for key in sorted(weights)}


def _uniform(prefix: str, seed: object, person_id: object) -> float:
    """The counter-based uniform in [0, 1) for one person."""
    seed_int = _integer("seed", seed)
    person_int = _integer("person_id", person_id)
    key = f"{prefix}|{seed_int:d}|{person_int:d}".encode("ascii")
    digest = hashlib.sha256(key).digest()
    return int.from_bytes(digest[:8], "big") / _TWO_TO_THE_64


def _pick(posterior: Mapping[int, float], uniform: float) -> int:
    """The first outcome whose cumulative weight exceeds ``uniform``."""
    cumulative = 0.0
    last_positive = None
    for outcome in sorted(posterior):
        weight = posterior[outcome]
        if weight > 0.0:
            last_positive = outcome
        cumulative += weight
        if cumulative > uniform:
            return outcome
    if last_positive is None:
        raise ValueError("the posterior has no positive weight")
    return last_positive


def claim_age_posterior(
    age: int,
    birth_year: int,
    sex: str,
    *,
    award_shares: AwardShares,
) -> dict[int, float]:
    """Weights over the whole claim ages a retired worker could have.

    ``award_shares(sex, entitlement_year)`` returns the share of
    retired-worker awards at each whole claim age from 62 to 70 in that
    year. For each claim age ``c`` from 62 to the smaller of 70 and
    ``age``, the weight is the share at ``c`` in entitlement year
    ``birth_year + c``. The weights come back normalised to one, keyed
    by every feasible claim age in rising order (a zero weight stays).

    Raises:
        ValueError: ``age`` is under 62, so no claim age is feasible;
            every weight is zero; or a share is negative or not finite.
        KeyError: ``award_shares`` gives no share for a feasible age.
        TypeError: ``age`` or ``birth_year`` is not an integer.
    """
    age_int = _integer("age", age)
    birth = _integer("birth_year", birth_year)
    if age_int < EARLIEST_CLAIM_AGE:
        raise ValueError(
            f"age {age_int} is under {EARLIEST_CLAIM_AGE}: no claim age is "
            "feasible"
        )
    weights: dict[int, float] = {}
    for claim_age in range(
        EARLIEST_CLAIM_AGE, min(LATEST_CLAIM_AGE, age_int) + 1
    ):
        year = birth + claim_age
        shares = award_shares(sex, year)
        if claim_age not in shares:
            raise KeyError(
                f"award_shares({sex!r}, {year}) gives no share at claim "
                f"age {claim_age}"
            )
        weights[claim_age] = _weight(
            f"share at claim age {claim_age} in {year}", shares[claim_age]
        )
    return _normalise(weights, f"age {age_int}, born {birth}, sex {sex!r}")


def draw_claim_age(
    person_id: int,
    age: int,
    birth_year: int,
    sex: str,
    *,
    award_shares: AwardShares,
    seed: int,
) -> int:
    """One whole claim age from :func:`claim_age_posterior`.

    The uniform is keyed by ``seed`` and ``person_id`` alone (see the
    module docstring), so the draw is a function of the person and the
    seed, not of the batch.

    Raises:
        TypeError: ``seed`` or ``person_id`` is not an integer, and every
            error :func:`claim_age_posterior` raises.
    """
    uniform = _uniform(CLAIM_AGE_KEY_PREFIX, seed, person_id)
    posterior = claim_age_posterior(
        age, birth_year, sex, award_shares=award_shares
    )
    return _pick(posterior, uniform)


def single_year_age(
    person_id: int,
    age_top_code: int,
    sex: str,
    *,
    age_shares: AgeShares,
    seed: int,
) -> int:
    """A single year of age for a person whose recorded age is a top code.

    The file stores ages 80 to 84 as 80, and 85 and over as 85.
    ``age_shares(top_code, sex)`` returns shares over the single years in
    that band; the function normalises them and draws one by the same
    recipe as :func:`draw_claim_age`, with ``single_year_age`` in place
    of ``claim_age`` in the key.

    Raises:
        ValueError: ``age_top_code`` is not a top code (80 or 85); a
            share is for an age outside the band, negative or not finite;
            or every share is zero.
        TypeError: ``age_top_code``, ``seed`` or ``person_id`` is not an
            integer.
    """
    code = _integer("age_top_code", age_top_code)
    if code not in TOP_CODE_BANDS:
        raise ValueError(
            f"age {code} is not a top code; expected one of "
            f"{sorted(TOP_CODE_BANDS)}"
        )
    low, high = TOP_CODE_BANDS[code]
    uniform = _uniform(SINGLE_YEAR_AGE_KEY_PREFIX, seed, person_id)
    weights: dict[int, float] = {}
    for single_age, share in age_shares(code, sex).items():
        single = _integer("single year of age", single_age)
        if single < low or (high is not None and single > high):
            raise ValueError(
                f"age {single} lies outside top code {code}'s band"
            )
        weights[single] = _weight(f"share at age {single}", share)
    if not weights:
        raise ValueError(f"age_shares gives no ages for top code {code}")
    return _pick(_normalise(weights, f"top code {code}"), uniform)
