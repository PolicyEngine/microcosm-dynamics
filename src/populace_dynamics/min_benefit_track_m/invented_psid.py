"""INVENTED PSID-shaped frames for the Track M cohort (plan items M4, M10).

INVENTED DATA - NOT A COMPARISON.  :func:`invented_cohort_inputs` draws,
from a seeded generator, the frames :func:`.cohort.load_cohort_inputs`
reads from the staged PSID: the 2023 anchor (sequence, relationship, age,
weight, the 2022 Social Security amount and its six type flags), the
design variables, death records, the marriage history, the earnings panel,
the person-level receipt histories of M3 (waves 1984-1992 and 2005-2023),
family-level rows and the next wave's year-before-last labor income.  No
PSID, Census, model or comparator value enters.  The shapes follow the
PSID's, so that :func:`.cohort.build_cohort` (M4) and
:func:`.careers.build_track_m_inputs` (M5) run end to end on it:

* family units of a single beneficiary, a couple (a spouse's link), a
  widow(er) with a late spouse who either received their own benefit or
  died before any own entitlement (a survivor's link), a beneficiary paid
  a dependent's or survivor's benefit only with no linkable worker (an
  unlinked auxiliary), and other family-unit members;
* old-age and disability-origin entitlements at invented ages, some
  families entering the PSID after 2005 (section 4b rule 3's later
  entrants), some persons observed receiving in 2004 with 2003 unknown;
* labor income observed every year 1968-1996 and even years 1998-2022
  for the reference person and spouse, and next-wave odd years 2001-2021.

Deterministic for a given seed.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.data import prior_year_labor_income as pyl
from populace_dynamics.data import social_security_receipt as ssr
from populace_dynamics.min_benefit_track_m import DRY_RUN_HEADER, structure
from populace_dynamics.min_benefit_track_m.cohort import TrackMCohortInputs

__all__ = ["INVENTED_LABEL", "invented_cohort_inputs"]

INVENTED_LABEL = DRY_RUN_HEADER
_PANEL_YEARS = (*range(1968, 1997), *range(1998, 2023, 2))
_TYPE_COLUMNS = {
    "disability": "type_disability",
    "retirement": "type_retirement",
    "survivor": "type_survivor",
    "dependent_of_disabled": "type_dependent_of_disabled",
    "dependent_of_retired": "type_dependent_of_retired",
    "other": "type_other",
}


class _Draw:
    def __init__(self, seed: int, threshold_years_from: int | None) -> None:
        self.rng = np.random.default_rng(seed)
        self.threshold_years_from = threshold_years_from
        self.anchor: list[dict[str, Any]] = []
        self.design: list[dict[str, Any]] = []
        self.deaths: list[dict[str, Any]] = []
        self.marriages: list[dict[str, Any]] = []
        self.earnings: list[dict[str, Any]] = []
        self.receipt: list[dict[str, Any]] = []
        self.family_level: list[dict[str, Any]] = []
        self.prior: list[dict[str, Any]] = []

    # -- helpers ---------------------------------------------------------
    def entitlement(self, birth: int) -> tuple[str, int]:
        """(basis, first year of own receipt) for a worker."""

        rng = self.rng
        if rng.random() < 0.18:
            onset_age = int(rng.integers(35, 61))
            return "disability", min(birth + onset_age + 1, 2022)
        age = int(rng.choice([62, 62, 62, 63, 64, 65, 65, 66, 66, 67, 70]))
        floor = self.threshold_years_from
        if floor is not None and birth + 62 < floor and birth + age > floor:
            # A worker whose year of attaining 62 precedes the captured
            # thresholds claims before the policy window opens.
            age = max(62, floor - birth)
        return "old_age", min(birth + age, 2022)

    def earnings_rows(
        self, pid: int, birth: int, last: int, role: str, wave_weight: float
    ) -> None:
        rng = self.rng
        start = birth + int(rng.integers(18, 25))
        level = float(np.exp(rng.normal(10.0, 0.6)))
        for year in _PANEL_YEARS:
            if year < start or year > last:
                continue
            if rng.random() < 0.08:
                continue  # an unobserved year
            amount = (
                0.0 if rng.random() < 0.1 else level * (1.02 ** (year - 1968))
            )
            self.earnings.append(
                {
                    "person_id": pid,
                    "period": year,
                    "earnings": round(amount, 0),
                    "earnings_acc": 0,
                    "role": role,
                    "age": year - birth,
                    "weight": wave_weight,
                }
            )
        for year in pyl.ODD_INCOME_YEARS:
            if start <= year <= min(last, 2021) and rng.random() < 0.85:
                self.prior.append(
                    {
                        "person_id": pid,
                        "wave": year + 2,
                        "income_year": year,
                        "role": (
                            "reference_person" if role == "head" else "spouse"
                        ),
                        "employed": 1,
                        "amount": round(level * 1.02 ** (year - 1968), 0),
                        "per": 6,
                        "acc": 0,
                        "status": "annual_amount",
                        "annual": round(level * 1.02 ** (year - 1968), 0),
                    }
                )

    def receipt_rows(
        self,
        pid: int,
        birth: int,
        first_own: int | None,
        own_types: tuple[str, ...],
        *,
        aux_from: int | None = None,
        aux_types: tuple[str, ...] = (),
        entered: int = 1984,
        last: int = 2023,
        unknown_2003_2004: bool = False,
    ) -> None:
        """Person-level rows for every wave the person is in a family."""

        for wave in ssr.INDIVIDUAL_WAVES:
            if wave < entered or wave > last or wave - 1 < birth + 16:
                continue
            year = wave - 1
            if unknown_2003_2004 and year < 2004:
                continue
            types: dict[str, Any] = dict.fromkeys(ssr.SS_TYPES, pd.NA)
            amount = 0
            if first_own is not None and year >= first_own:
                amount = 12_000
                for name in ssr.SS_TYPES:
                    types[name] = name in own_types
            elif aux_from is not None and year >= aux_from:
                amount = 9_000
                for name in ssr.SS_TYPES:
                    types[name] = name in aux_types
            self.receipt.append(
                {
                    "person_id": pid,
                    "wave": wave,
                    "income_year": year,
                    "relationship": 10,
                    "interview": 0,
                    "amount": amount,
                    "acc": 0,
                    **{f"type_{name}": types[name] for name in ssr.SS_TYPES},
                    "type_combination": False,
                }
            )

    def family_none(self, pid: int, year: int, source: str) -> None:
        """A family-level observation of no receipt (M3's reading: a
        family reporting none identifies every member's non-receipt)."""

        self.family_level.append(
            {
                "person_id": pid,
                "income_year": year,
                "source": source,
                "receipt": False,
                "fu_size": 1,
                **{f"type_{name}": pd.NA for name in ssr.SS_TYPES},
            }
        )

    def person(
        self,
        pid: int,
        interview: int,
        relationship: int,
        birth: int,
        sex: str,
        weight: float,
        design: dict[str, int],
        amount_2022: int,
        types_2022: tuple[str, ...],
    ) -> None:
        flags = {
            column: (
                (1 if name in types_2022 else 5) if amount_2022 > 0 else 0
            )
            for name, column in _TYPE_COLUMNS.items()
        }
        self.anchor.append(
            {
                "person_id": pid,
                "interview": interview,
                "sequence": 1 if relationship == 10 else 2,
                "relationship": relationship,
                "age": 2023 - birth,
                "reported_birth_year": birth,
                "weight": weight,
                "ss_amount": amount_2022,
                "ss_acc": 0,
                **flags,
            }
        )
        self.design.append({"person_id": pid, **design})
        self.deaths.append(
            {
                "person_id": pid,
                "sex_code": 1 if sex == "male" else 2,
                "sex": sex,
                "death_code": 0,
                "death_status": "not_deceased",
                "death_year": pd.NA,
                "death_year_lo": pd.NA,
                "death_year_hi": pd.NA,
            }
        )

    def marriage(
        self,
        pid: int,
        birth: int,
        sex: str,
        spouse: int | None,
        *,
        start: int,
        how: str,
        end: int | None,
    ) -> None:
        self.marriages.append(
            {
                "person_id": pid,
                "sex": sex,
                "birth_year": birth,
                "birth_month": 6,
                "marriage_order": 1,
                "spouse_person_id": spouse,
                "start_year": start,
                "start_month": 6,
                "end_year": end,
                "end_month": 6 if end is not None else pd.NA,
                "separation_year": pd.NA,
                "separation_month": pd.NA,
                "how_ended": how,
                "last_known_status": (
                    "married" if how == "intact" else "widowed"
                ),
                "most_recent_report_year": 2023,
                "n_marriages": 1,
                "n_records": 1,
                "is_marriage": True,
            }
        )


def _frame(rows: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns)


def invented_cohort_inputs(
    *,
    seed: int = 0,
    n_family_units: int = 300,
    threshold_years_from: int | None = 2003,
) -> TrackMCohortInputs:
    """INVENTED cohort inputs in the PSID's shapes (module docstring).

    ``threshold_years_from`` (2003, the first year of the invented
    thresholds, ``invented.INVENTED_THRESHOLD_YEARS``) keeps every record
    in a policy window to threshold years from that year on: a worker
    whose year of attaining 62 precedes it claims before the window
    opens, and a late spouse who died before any own entitlement died in
    or after it.  ``None`` draws without that constraint, as the PSID is
    (its in-window records need years before 2003), so that the dry run
    can show the pipeline refusing, before computing, a cohort that needs
    a threshold year the real capture lacks (one of 1983-1985, 1987, 1990
    and 1993, or a year before 1982).
    """

    draw = _Draw(seed, threshold_years_from)
    rng = draw.rng
    kinds = ("single", "couple", "widowed", "aux_only", "entrant")
    for unit in range(n_family_units):
        interview = unit + 1
        kind = str(rng.choice(kinds, p=[0.3, 0.4, 0.17, 0.05, 0.08]))
        design = {
            "stratum": int(rng.integers(1, 21)),
            "cluster": int(rng.integers(1, 3)),
        }
        weight = round(float(np.exp(rng.normal(8.4, 0.5))), 1)
        base = interview * 1000
        birth = int(rng.integers(1930, 1961))
        sex = str(rng.choice(["male", "female"]))
        if kind == "aux_only":
            pid = base + 1
            draw.person(
                pid,
                interview,
                10,
                birth,
                "female",
                weight,
                design,
                9_000,
                ("dependent_of_retired",),
            )
            draw.receipt_rows(
                pid,
                birth,
                None,
                (),
                aux_from=birth + 62,
                aux_types=("dependent_of_retired",),
            )
            draw.marriage(
                pid,
                birth,
                "female",
                None,
                start=birth + 25,
                how="intact",
                end=None,
            )
            continue
        basis, first = draw.entitlement(birth)
        own_types = (basis if basis == "disability" else "retirement",)
        pid = base + 1
        draw.person(
            pid, interview, 10, birth, sex, weight, design, 12_000, own_types
        )
        entered = 2011 if kind == "entrant" else 1984
        draw.receipt_rows(
            pid,
            birth,
            first,
            own_types,
            entered=entered,
            unknown_2003_2004=rng.random() < 0.05,
        )
        # Family-level non-receipt (the 2005 wave's year-before-last "no"
        # for 2003, a zero family total for 2002) for some who had not
        # yet claimed: section 4b rule 3's 2003 boundary.
        if kind != "entrant" and first > 2003 and rng.random() < 0.3:
            draw.family_none(pid, 2003, "year_before_last")
        if kind != "entrant" and first > 2002 and rng.random() < 0.3:
            draw.family_none(pid, 2002, "total")
        draw.earnings_rows(pid, birth, 2022, "head", weight)
        if kind in ("single", "entrant"):
            draw.marriage(
                pid,
                birth,
                sex,
                None,
                start=birth + 24,
                how="divorce",
                end=birth + 30,
            )
            continue
        if kind == "couple":
            spouse = base + 2
            spouse_birth = int(
                np.clip(birth + rng.integers(-4, 5), 1930, 1960)
            )
            spouse_sex = "female" if sex == "male" else "male"
            has_own = rng.random() < 0.8
            s_basis, s_first = draw.entitlement(spouse_birth)
            s_types = (
                (s_basis if s_basis == "disability" else "retirement",)
                if has_own
                else ("dependent_of_retired",)
            )
            draw.person(
                spouse,
                interview,
                20,
                spouse_birth,
                spouse_sex,
                weight,
                design,
                8_000,
                s_types,
            )
            if has_own:
                draw.receipt_rows(spouse, spouse_birth, s_first, s_types)
                draw.earnings_rows(
                    spouse, spouse_birth, 2022, "spouse", weight
                )
            else:
                draw.receipt_rows(
                    spouse,
                    spouse_birth,
                    None,
                    (),
                    aux_from=max(spouse_birth + 62, first),
                    aux_types=("dependent_of_retired",),
                )
            start = min(birth, spouse_birth) + 25
            draw.marriage(
                pid, birth, sex, spouse, start=start, how="intact", end=None
            )
            draw.marriage(
                spouse,
                spouse_birth,
                spouse_sex,
                pid,
                start=start,
                how="intact",
                end=None,
            )
            if rng.random() < 0.1:
                member = base + 3
                m_birth = int(rng.integers(1928, 1945))
                m_basis, m_first = draw.entitlement(m_birth)
                m_types = (
                    m_basis if m_basis == "disability" else "retirement",
                )
                draw.person(
                    member,
                    interview,
                    50,
                    m_birth,
                    "female",
                    weight,
                    design,
                    10_000,
                    m_types,
                )
                draw.receipt_rows(member, m_birth, m_first, m_types)
                draw.marriages.append(
                    {
                        "person_id": member,
                        "sex": "female",
                        "birth_year": m_birth,
                        "birth_month": pd.NA,
                        "marriage_order": pd.NA,
                        "spouse_person_id": pd.NA,
                        "start_year": pd.NA,
                        "start_month": pd.NA,
                        "end_year": pd.NA,
                        "end_month": pd.NA,
                        "separation_year": pd.NA,
                        "separation_month": pd.NA,
                        "how_ended": "never_married",
                        "last_known_status": "never_married",
                        "most_recent_report_year": 2023,
                        "n_marriages": 0,
                        "n_records": 1,
                        "is_marriage": False,
                    }
                )
            continue
        # widowed: a late spouse who received, or died before entitlement
        late = base + 9
        late_birth = int(np.clip(birth + rng.integers(-5, 4), 1920, 1960))
        # Died before 62 (after 1985) or at 66 or older (by 2021); a
        # late spouse born too early to die before 62 after 1985 dies old.
        early_low = max(late_birth + 45, draw.threshold_years_from or 1985)
        early_high = min(late_birth + 61, 2021)
        died_early = early_low <= early_high and rng.random() < 0.4
        if died_early:
            death = int(rng.integers(early_low, early_high + 1))
        else:
            # Under the capture constraint a late spouse who died old is
            # alive at the 2005 wave, so its own receipt is observed.
            floor = draw.threshold_years_from
            earliest = 1990 if floor is None else floor + 3
            death = int(
                rng.integers(min(max(late_birth + 66, earliest), 2021), 2022)
            )
        late_basis, late_first = draw.entitlement(late_birth)
        if not died_early:
            late_first = min(late_first, death - 1)
            draw.receipt_rows(
                late, late_birth, late_first, ("retirement",), last=death
            )
        draw.earnings_rows(late, late_birth, death - 1, "head", weight)
        late_sex = "male" if sex == "female" else "female"
        draw.deaths.append(
            {
                "person_id": late,
                "sex_code": 1 if late_sex == "male" else 2,
                "sex": late_sex,
                "death_code": death,
                "death_status": "exact",
                "death_year": death,
                "death_year_lo": death,
                "death_year_hi": death,
            }
        )
        start = min(birth, late_birth) + 24
        draw.marriage(
            pid, birth, sex, late, start=start, how="widowhood", end=death
        )
        draw.marriage(
            late,
            late_birth,
            late_sex,
            pid,
            start=start,
            how="intact",
            end=None,
        )
        survivor_from = max(death, birth + 60)
        # the widow(er) mentions a survivor's benefit from then on
        for row in draw.receipt:
            if row["person_id"] == pid and row["income_year"] >= survivor_from:
                row["type_survivor"] = True
                if row["amount"] == 0:
                    row["amount"] = 9_000
                    for name in ssr.SS_TYPES:
                        row[f"type_{name}"] = name == "survivor"
        for row in draw.anchor:
            if row["person_id"] == pid:
                row["type_survivor"] = 1
    anchor = pd.DataFrame(draw.anchor)
    anchor["reported_birth_year"] = anchor["reported_birth_year"].astype(
        "Int64"
    )
    deaths = pd.DataFrame(draw.deaths)
    for column in ("death_year", "death_year_lo", "death_year_hi"):
        deaths[column] = deaths[column].astype("Int64")
    marriages = pd.DataFrame(draw.marriages)
    for column in (
        "birth_year",
        "birth_month",
        "marriage_order",
        "spouse_person_id",
        "start_year",
        "start_month",
        "end_year",
        "end_month",
        "separation_year",
        "separation_month",
        "n_marriages",
    ):
        marriages[column] = marriages[column].astype("Int64")
    earnings = pd.DataFrame(draw.earnings)
    receipt = pd.DataFrame(draw.receipt)
    for name in ssr.SS_TYPES:
        receipt[f"type_{name}"] = receipt[f"type_{name}"].astype("boolean")
    family_level = pd.DataFrame(
        draw.family_level,
        columns=[
            "person_id",
            "income_year",
            "source",
            "receipt",
            "fu_size",
            *[f"type_{name}" for name in ssr.SS_TYPES],
        ],
    )
    for name in ssr.SS_TYPES:
        family_level[f"type_{name}"] = family_level[f"type_{name}"].astype(
            "boolean"
        )
    structure_inputs = structure.TrackMStructureInputs(
        anchor=anchor,
        family_social_security=pd.DataFrame(
            columns=[
                "interview",
                "rp_amount",
                "rp_acc",
                "spouse_amount",
                "spouse_acc",
            ]
        ),
        death_records=deaths,
        marriage_history=marriages,
        observed_earnings=earnings,
        design=pd.DataFrame(draw.design),
        codes={},
        provenance={"label": INVENTED_LABEL, "seed": seed},
    )
    return TrackMCohortInputs(
        structure_inputs=structure_inputs,
        individual_receipt=receipt,
        family_1993_receipt=receipt.iloc[0:0].copy(),
        family_level_receipt=family_level,
        prior_year_labor=pd.DataFrame(draw.prior),
        provenance={
            "label": INVENTED_LABEL,
            "generator": "min_benefit_track_m.invented_psid",
            "seed": seed,
            "n_family_units": n_family_units,
        },
    )
