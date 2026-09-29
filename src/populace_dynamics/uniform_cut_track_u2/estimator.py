"""The U2 income concept: U1's concept with an explicit U2 context.

Specification sections 4-8 and 14 ("Income estimator: explicit U2
parameter and role context; preserve U1 pins at
``S/estimates/adjusted_poverty.py:196`` and IRA-year behavior at
``:290``").  U2 inherits U1's pre-tax family money-income basis, asset
annuity, thresholds, cut and SSI response unchanged.  This module does not
edit or re-pin :mod:`populace_dynamics.estimates.adjusted_poverty`; it
calls the same computation primitives with a U2 parameter object and adds
the U2 guards:

* **Parameters.**  :class:`U2IncomeSpec` carries the section 15 values
  (every field of U1's ``AdjustedPovertySpec`` plus ``target_id``) and
  refuses what U2 does not register: ``member_rule`` annuity lives, the
  ``recipients_only`` deeming bound, a cut start other than 2004, and an
  interest rate other than the 3 percent primary or the 2 percent
  unscored sensitivity.  Rows are validated by U1's own spec class.
* **IRA income years.**  U1 removes ``HEAD IRAS`` only in income year
  2012 (``_HEAD_IRA_INCOME_YEARS``, derived from U1's wave tuple).  Every
  U2 wave's family file carries ``HEAD IRAS`` (milestone 1 income
  registry, ``income.<wave>.head_iras``), so U2 removes the head's
  annuity and IRA income in every income year 2012-2022 and refuses a
  row without ``head_iras``.  U1's constant is untouched.
* **Role context.**  :class:`U2EstimatorContext` names the role context
  the rows were built under (``registry`` or ``invented_declared``) and
  the target; the rows' ``attrs`` must agree, a registered run needs the
  registry context, and the invented declared context runs only on
  invented rows.  The income units follow the section 3 income slots
  already on the rows: ``member_role`` (head, the spouse slot ``wife``,
  or ``ofum``, which includes codes 90 and 92), ``wife_present`` (the
  designated spouse income slot) and the head/legal-spouse annuity
  lives.
* **Provenance.**  As U1: ``invented`` for tests and dry runs;
  ``registered_real`` needs an issue #42 pointer and rows built from
  sealed PSID files.  Thresholds and SSI must be U2-bound (or invented in
  an invented run); U1's captures are refused by hash.

Output columns equal U1's :func:`~populace_dynamics.estimates.
adjusted_poverty.adjusted_incomes`; ``attrs`` add ``target_id`` and the
role context.  A differential test holds the two equal on rows both
accept.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import identity, sources

__all__ = [
    "HEAD_IRA_INCOME_YEARS",
    "REQUIRED_COLUMNS",
    "U2EstimatorContext",
    "U2EstimatorError",
    "U2IncomeSpec",
    "u2_adjusted_incomes",
]

#: Income years whose family file carries HEAD IRAS: every U2 wave's
#: (income years 2012-2022; milestone 1 registry ``income.<wave>.
#: head_iras``, e.g. ER58073 in 2013 and ER77365 in 2019).
HEAD_IRA_INCOME_YEARS: frozenset[int] = frozenset(
    wave - 1 for wave in sources.SUPPORT_WAVES
)
#: The row columns the U2 concept reads: U1's plus ``head_iras``.
REQUIRED_COLUMNS: tuple[str, ...] = (*ap.REQUIRED_COLUMNS, "head_iras")
_REGISTERED_INTEREST = (0.03, 0.02)


class U2EstimatorError(ValueError):
    """The rows, parameters or context cannot yield the U2 concept."""


_AP_FIELDS = tuple(f.name for f in fields(ap.AdjustedPovertySpec))


@dataclass(frozen=True)
class U2IncomeSpec:
    """The U2 income-concept parameters (section 15; U1's key names)."""

    cut_rate: float = 0.13
    cut_start_year: int | None = 2004
    annuitized_share: float = 0.8
    real_interest_rate: float = 0.03
    annuity_timing: str = "immediate"
    annuity_load: float = 0.0
    survivor_share: float = 0.5
    mortality_basis: str = "nchs_2000"
    terminal_closure: str = "table_end"
    asset_income_rule: str = "replace"
    income_unit: str = "family_unit"
    financial_assets: str = "wealth1"
    retirement_account_income_rule: str = "remove_head"
    farm_asset_share: float = 0.5
    annuity_lives: str = "fu_head_rule"
    negative_wealth_rule: str = "annuity_floored_at_zero"
    threshold_rule: str = "census_weighted_average_65plus"
    ssi_rule: str = "offset_existing_recipients"
    ssi_deeming: str = "spouse_social_security_counted"
    ofum_ssi_unit: str = "single_individual"
    target_id: str = identity.TARGET_ID

    def __post_init__(self) -> None:
        identity.check_target(self.target_id, "U2IncomeSpec")
        try:
            self.inherited()
        except ap.AdjustedPovertyError as error:
            raise U2EstimatorError(str(error)) from error
        if self.annuity_lives != "fu_head_rule":
            raise U2EstimatorError(
                "U2 prices annuities on the section 3 head and legal-spouse "
                "lives (fu_head_rule) only"
            )
        if self.ssi_deeming != "spouse_social_security_counted":
            raise U2EstimatorError(
                "U2 registers full attribution of spouse-slot Social "
                "Security only (section 8)"
            )
        if self.cut_start_year != 2004:
            raise U2EstimatorError("U2's cut starts in 2004 (section 7)")
        if float(self.real_interest_rate) not in _REGISTERED_INTEREST:
            raise U2EstimatorError(
                "U2 registers 3 percent real interest and the 2 percent "
                "unscored sensitivity only (section 5)"
            )

    def inherited(self) -> ap.AdjustedPovertySpec:
        """The same values as U1's spec class (validated by it)."""

        return ap.AdjustedPovertySpec(
            **{name: getattr(self, name) for name in _AP_FIELDS}
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class U2EstimatorContext:
    """The explicit role context and target the rows were built under."""

    role_context: str
    target_id: str = identity.TARGET_ID

    def __post_init__(self) -> None:
        identity.check_target(self.target_id, "U2EstimatorContext")
        if self.role_context not in sources.ROLE_CONTEXT_KINDS:
            raise U2EstimatorError(
                f"role context must be one of {sources.ROLE_CONTEXT_KINDS}"
            )


def _check_guards(
    rows: pd.DataFrame,
    spec: U2IncomeSpec,
    context: U2EstimatorContext,
    data_provenance: str,
    registration_pointer: Any,
    life_table: ap.LifeTable,
    thresholds: ap.PovertyThresholds | None,
    ssi: ap.SsiParameters | None,
) -> None:
    if not isinstance(spec, U2IncomeSpec):
        raise U2EstimatorError("spec must be a U2IncomeSpec")
    if not isinstance(context, U2EstimatorContext):
        raise U2EstimatorError("a U2 estimate needs a U2EstimatorContext")
    if not isinstance(rows, pd.DataFrame):
        raise U2EstimatorError("rows must be a DataFrame")
    identity.check_target(rows.attrs.get("target_id"), "the income rows")
    if rows.attrs.get("role_context") != context.role_context:
        raise U2EstimatorError(
            f"the rows were built under role context "
            f"{rows.attrs.get('role_context')!r}, not {context.role_context!r}"
        )
    kind = rows.attrs.get("provenance_kind")
    if data_provenance not in ap.DATA_PROVENANCES:
        raise U2EstimatorError(
            f"data_provenance must be one of {ap.DATA_PROVENANCES}"
        )
    if data_provenance == ap.REGISTERED_REAL:
        if not isinstance(registration_pointer, str) or not (
            registration_pointer.strip()
        ):
            raise U2EstimatorError(
                "registered_real requires the issue #42 registration pointer"
            )
        if kind != "psid_files":
            raise U2EstimatorError(
                f"data_provenance 'registered_real' contradicts the rows' "
                f"provenance {kind!r}"
            )
        if context.role_context != sources.REGISTRY:
            raise U2EstimatorError(
                "a registered U2 run applies the committed roles registry, "
                "never the invented declared role context"
            )
    else:
        if kind == "psid_files":
            raise U2EstimatorError(
                "rows built from staged PSID files cannot be processed as "
                "invented data"
            )
        if kind != "invented" and context.role_context == (
            sources.INVENTED_DECLARED
        ):
            raise U2EstimatorError(
                "the invented declared role context applies only to "
                "invented rows"
            )
    if life_table.name == ap.INVENTED_LIFE_TABLE:
        if data_provenance == ap.REGISTERED_REAL:
            raise U2EstimatorError(
                "a registered_real run cannot use an invented life table"
            )
    elif life_table.name != spec.mortality_basis:
        raise U2EstimatorError(
            f"life table {life_table.name!r} is not the spec's "
            f"{spec.mortality_basis!r}"
        )
    for name, value in (("thresholds", thresholds), ("ssi", ssi)):
        provenance = dict(getattr(value, "provenance", {}) or {})
        sha = provenance.get("sha256")
        if sha in (identity.U1_THRESHOLDS_SHA256, identity.U1_SSI_SHA256):
            raise U2EstimatorError(
                f"the {name} are a U1 capture; U2 refuses them (section 14)"
            )
        if value is None:
            continue
        if provenance.get("kind") == ap.INVENTED:
            if data_provenance == ap.REGISTERED_REAL:
                raise U2EstimatorError(
                    f"a registered_real run cannot use invented {name}"
                )
        elif provenance.get("target_id") != identity.TARGET_ID:
            raise U2EstimatorError(
                f"the {name} are not bound to U2 (provenance {provenance!r})"
            )


def _head_retirement_account_income(rows: pd.DataFrame) -> np.ndarray:
    """HEAD ANNUITIES plus HEAD IRAS in every U2 income year (F4a)."""

    years = rows["income_year"].astype("int64").to_numpy()
    outside = ~np.isin(years, sorted(HEAD_IRA_INCOME_YEARS))
    if outside.any():
        raise U2EstimatorError(
            f"income years {sorted(set(years[outside].tolist()))} are not "
            "U2 income years"
        )
    iras = pd.to_numeric(rows["head_iras"], errors="raise")
    if iras.isna().any():
        raise U2EstimatorError(
            "head_iras missing: every U2 family file carries HEAD IRAS"
        )
    return rows["head_annuities"].to_numpy(dtype=np.float64) + iras.to_numpy(
        dtype=np.float64
    )


def u2_adjusted_incomes(
    rows: pd.DataFrame,
    spec: U2IncomeSpec | None = None,
    *,
    context: U2EstimatorContext,
    data_provenance: str,
    life_table: ap.LifeTable,
    thresholds: ap.PovertyThresholds | None,
    ssi: ap.SsiParameters | None,
    registration_pointer: str | None = None,
) -> pd.DataFrame:
    """Baseline and reform adjusted income and poverty status per row.

    The computation is U1's (the same primitives of
    :mod:`populace_dynamics.estimates.adjusted_poverty`, in the same
    order): money income less the replaced asset income, the head's
    annuity and IRA income and the imputed farm asset income, plus the
    annuity on 80 percent of financial assets floored at zero; reform
    income subtracts the cut on the unit's Social Security and adds the
    SSI response; poor when income is strictly below the threshold.
    """

    spec = U2IncomeSpec() if spec is None else spec
    _check_guards(
        rows,
        spec,
        context,
        data_provenance,
        registration_pointer,
        life_table,
        thresholds,
        ssi,
    )
    missing = [c for c in REQUIRED_COLUMNS if c not in rows.columns]
    if missing:
        raise U2EstimatorError(f"rows lack columns {missing}")
    if rows["observation_id"].duplicated().any():
        raise U2EstimatorError("duplicate observation_id")
    roles = set(rows["member_role"].astype(str))
    if not roles <= set(ap.MEMBER_ROLES):
        raise U2EstimatorError(
            f"member_role outside {ap.MEMBER_ROLES}: {sorted(roles)}"
        )
    attrs = dict(rows.attrs)
    rows = rows.reset_index(drop=True)
    inherited = spec.inherited()
    units = ap._unit_frame(rows, inherited)
    employer_dc = ap._employer_dc(rows, inherited)
    assets = rows["wealth1"].to_numpy(dtype=np.float64) + employer_dc
    annuitized = inherited.annuitized_share * np.maximum(assets, 0.0)
    factors, bases = ap._annuity_factors(rows, inherited, life_table)
    if not np.all(factors > 0):
        raise U2EstimatorError("non-positive annuity factor")
    annuity = annuitized / factors
    replace = inherited.asset_income_rule == "replace"
    zeros = np.zeros(len(rows), dtype=np.float64)
    retirement_removed = (
        _head_retirement_account_income(rows)
        if replace
        and inherited.retirement_account_income_rule == "remove_head"
        else zeros
    )
    farm_removed = ap._farm_asset_income(rows, inherited) if replace else zeros
    removed = (
        (units["asset_income"] if replace else zeros)
        + retirement_removed
        + farm_removed
    )
    baseline = units["money"] - removed + annuity
    applies = ap.cut_applies(rows, inherited)
    cut_rates = np.where(applies, inherited.cut_rate, 0.0)
    cut = cut_rates * units["social_security"]
    offset, new = ap._ssi_response(rows, inherited, units, ssi, cut_rates)
    reform = baseline - cut + offset + new
    thresholds_out = np.zeros(len(rows), dtype=np.float64)
    cells: list[str] = []
    for i, row in enumerate(rows.itertuples(index=False)):
        value, cell = ap.threshold_for(
            thresholds,
            int(row.income_year),
            int(units["size"][i]),
            int(units["children"][i]),
            inherited.threshold_rule,
            needs_standard=float(row.census_needs_standard),
        )
        thresholds_out[i] = value
        cells.append(cell)
    for name, values in (
        ("baseline_income", baseline),
        ("reform_income", reform),
        ("annuity", annuity),
        ("threshold", thresholds_out),
    ):
        if not np.all(np.isfinite(values)):
            raise U2EstimatorError(f"non-finite {name}")
    out = pd.DataFrame(
        {
            "observation_id": rows["observation_id"],
            "family_unit_id": rows["family_unit_id"],
            "income_basis": np.where(units["fu"], "family_unit", "head_wife"),
            "money_income": units["money"],
            "asset_income_reported": units["asset_income"],
            "retirement_account_income_removed": retirement_removed,
            "farm_asset_income_removed": farm_removed,
            "asset_income_removed": removed,
            "employer_dc_added": employer_dc,
            "financial_assets": assets,
            "annuity_basis": bases,
            "annuity_factor": factors,
            "annuity": annuity,
            "baseline_income": baseline,
            "social_security": units["social_security"],
            "cut_applies": applies,
            "cut": cut,
            "ssi_offset": offset,
            "ssi_new": new,
            "reform_income": reform,
            "unit_size": units["size"],
            "threshold": thresholds_out,
            "threshold_cell": cells,
        }
    )
    out["poor_baseline"] = out["baseline_income"] < out["threshold"]
    out["poor_reform"] = out["reform_income"] < out["threshold"]
    out.attrs["provenance_kind"] = attrs.get("provenance_kind")
    out.attrs["data_provenance"] = data_provenance
    out.attrs["spec"] = spec.as_dict()
    out.attrs["life_table"] = life_table.name
    out.attrs["target_id"] = identity.TARGET_ID
    out.attrs["role_context"] = context.role_context
    return out
