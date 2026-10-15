"""Enumerate G's finite invented configuration coverage denominator.

Verification class: statutory conformance. This artifact admits gross
benefits for supported invented configurations only. It contains no real
data and makes no population, behavioral, payment-timing or forecast claim.
All records and people below are invented; the parameter fixture uses SSA's
captured published NAWI and statutory age schedules. The statutory-example
registry is counted separately from the invented configuration denominator.

The lattice calls G's standalone snapshot API. Monthly histories still need
the per-record 403(a)(5) guard. Separate named refusal witnesses exercise
historical, multi-record and guarded-path reasons outside the finite lattice.
G's rules are 202/203/215 (42 U.S.C. 402/403/415); redistribution follows
GN 02603.045/.050, and the supported scope is documented in the G note.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path

import yaml

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "tests/data/track_b/gross_benefit_examples.yaml"
DEFAULT_OUTPUT = ROOT / "docs/design/track_b_g_conformance_report.json"
PARAMS = ssa_params()
DUAL_MODES = (
    "none",
    "rib_unreduced_b",
    "rib_unreduced_c",
    "rib_reduced_b",
    "rib_reduced_c",
    "rib_credited_c",
    "dib_b",
    "dib_c",
)
REDUCTION_FLAGS = (0, 36)
CHILD_IN_CARE_FLAGS = (None, False, "entitled_child")
PAYMENT_ERAS = {
    "before_october_1999": g.YearMonth(1999, 9),
    "october_1999_through_december_2023": g.YearMonth(2023, 12),
    "from_january_2024": g.YearMonth(2024, 1),
}
ROLE_ORDER = tuple(g.Role)
ROLE_INDEX = {role: index for index, role in enumerate(ROLE_ORDER)}
MAX_ROLE_MULTISET_SIZE = 2
NOW = g.YearMonth(2026, 1)


@dataclass(frozen=True)
class Configuration:
    """One cell of the documented finite invented Cartesian product."""

    kind: g.FamilyKind
    roles: tuple[g.Role, ...]
    dual_mode: str
    reduction_months: int
    payment_era: str
    condition_scope: str = "none"
    condition: g.RecordCondition | g.BeneficiaryCondition | None = None
    child_in_care: str | bool | None = False

    @property
    def key(self) -> tuple:
        return (
            self.kind.value,
            tuple(role.value for role in self.roles),
            self.dual_mode,
            self.reduction_months,
            self.payment_era,
            self.condition_scope,
            self.condition.value if self.condition else None,
            self.child_in_care,
        )


def declared_conditions() -> tuple[tuple[str, object], ...]:
    """No condition, each single record flag, each single beneficiary flag."""
    return (
        ("none", None),
        *(("record", condition) for condition in g.RecordCondition),
        *(("beneficiary", condition) for condition in g.BeneficiaryCondition),
    )


def role_multisets() -> tuple[tuple[g.Role, ...], ...]:
    return tuple(
        roles
        for size in range(MAX_ROLE_MULTISET_SIZE + 1)
        for roles in itertools.combinations_with_replacement(ROLE_ORDER, size)
    )


def configurations() -> Iterator[Configuration]:
    for (
        kind,
        roles,
        dual,
        reductions,
        era,
        declared,
        care,
    ) in itertools.product(
        tuple(g.FamilyKind),
        role_multisets(),
        DUAL_MODES,
        REDUCTION_FLAGS,
        tuple(PAYMENT_ERAS),
        declared_conditions(),
        CHILD_IN_CARE_FLAGS,
    ):
        scope, condition = declared
        yield Configuration(
            kind, roles, dual, reductions, era, scope, condition, care
        )


def _retired(pia=F(1000), maximum=F(1500), **extra):
    return g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        maximum,
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
        **extra,
    )


def _survivor(**extra):
    # Invented snapshots explicitly exclude protected May 1978 entitlement.
    extra.setdefault("widow_drc_savings_clause", False)
    return g.RecordState(g.FamilyKind.SURVIVOR, F(1000), F(1750), **extra)


def _family(state, members=(), month=NOW):
    return g.family_benefits(
        state,
        members,
        payment_month=month,
        params=PARAMS,
        standalone=True,
    )


def _own_benefit(mode):
    if mode == "none":
        return None
    if mode.startswith("dib_"):
        return g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(100))
    return g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE,
        F(100),
        reduction_months=36 if mode.startswith("rib_reduced_") else 0,
        delayed_credit_months=12 if mode == "rib_credited_c" else 0,
        birth_year=1946,
    )


def compute_configuration(case: Configuration):
    """Build a cell exactly as described in the report's lattice header."""
    if not case.roles and (
        case.dual_mode != "none"
        or case.reduction_months
        or case.condition_scope == "beneficiary"
    ):
        raise g.InvalidFamilyInput(
            "A focal-beneficiary flag needs at least one beneficiary"
        )
    conditions = (
        {case.condition} if case.condition_scope == "record" else set()
    )
    worker = None
    if case.kind is g.FamilyKind.RETIREMENT and (
        g.RecordCondition.WORKER_NOT_ENTITLED not in conditions
    ):
        worker = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000))
    state = g.RecordState(
        case.kind,
        F(1000),
        F(1750) if case.kind is g.FamilyKind.SURVIVOR else F(1500),
        widow_drc_savings_clause=False,
        worker=worker,
        conditions=conditions,
        source="invented conformance lattice; given current PIA and maximum",
    )
    members = []
    children = [
        f"b{index}"
        for index, role in enumerate(case.roles)
        if role is g.Role.CHILD
    ]
    for index, role in enumerate(case.roles):
        fields = {}
        if index == 0:
            fields["reduction_months"] = case.reduction_months
            own = _own_benefit(case.dual_mode)
            fields["own_benefit"] = own
            if own is not None:
                fields["own_benefit_first"] = case.dual_mode.endswith("_c")
            fields["birth_year"] = 1946
            if case.condition_scope == "beneficiary":
                fields["conditions"] = {case.condition}
        if role in (g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE):
            fields["reduction_period_months"] = 72
            fields.setdefault("birth_year", 1946)
        if role in (
            g.Role.WIDOW,
            g.Role.SURVIVING_DIVORCED_SPOUSE,
            g.Role.DISABLED_WIDOW,
            g.Role.DIVORCED_SPOUSE,
        ):
            fields["child_in_care"] = (
                (children[0] if children else "absent_child")
                if case.child_in_care == "entitled_child"
                else case.child_in_care
            )
        if role is g.Role.DIVORCED_SPOUSE:
            fields["first_entitlement_child_in_care"] = False
        members.append(g.Beneficiary(f"b{index}", role, **fields))
    return _family(state, members, PAYMENT_ERAS[case.payment_era])


def classify_configuration(case: Configuration) -> tuple[str, str | None]:
    """Keep every cell; invalid inputs never become coverage refusals."""
    try:
        outcome = g.evaluate_family(
            case.key.__repr__(), 1, lambda: compute_configuration(case)
        )
    except g.InvalidFamilyInput:
        return "invalid", None
    if outcome.supported:
        return "supported", None
    return "refused", outcome.unsupported.reason.value


def _savings_witness(*, unknown=False):
    month = g.YearMonth(2025, 11)
    children = [g.Beneficiary(c, g.Role.CHILD) for c in ("c1", "c2")]
    guard = g.SavingsClauseGuard(month, earlier_months_unknown=unknown)
    guard.admit(_family(_retired(), children, month))
    guard.admit(
        _family(
            _retired(F("1000.10"), F(1500)),
            children,
            g.YearMonth(2025, 12),
        )
    )


def refusal_witnesses() -> dict[g.UnsupportedReason, tuple[str, Callable]]:
    """One independently constructed witness for every retained reason."""
    rib, dib = g.OwnBenefitKind.OLD_AGE, g.OwnBenefitKind.DISABILITY
    reasons = g.UnsupportedReason

    def multiple_records(child):
        first_role = g.Role.CHILD if child else g.Role.DIVORCED_SPOUSE
        second_role = g.Role.CHILD if child else g.Role.MOTHER_FATHER
        return g.household_benefits(
            {
                "first": g.HouseholdRecord(
                    "a", _retired(), [g.Beneficiary("person", first_role)]
                ),
                "second": g.HouseholdRecord(
                    "dead", _survivor(), [g.Beneficiary("person", second_role)]
                ),
            },
            payment_month=NOW,
            params=PARAMS,
        )

    return {
        reasons.ELIGIBILITY_BEFORE_1983: (
            "1982 eligibility with otherwise valid survivor inputs",
            lambda: _family(
                g.record_state(
                    g.WorkerRecord(g.FamilyKind.SURVIVOR, 1982, F(500)), PARAMS
                )
            ),
        ),
        reasons.PAYMENT_MONTH_BEFORE_1983: (
            "December 1982 benefit month",
            lambda: _family(_survivor(), month=g.YearMonth(1982, 12)),
        ),
        reasons.DI_ENTITLEMENT_BEFORE_JULY_1980: (
            "Initial DIB entitlement June 1980",
            lambda: _family(
                g.record_state(
                    g.WorkerRecord(
                        g.FamilyKind.DISABILITY,
                        1985,
                        F(500),
                        aime=700,
                        first_dib_entitlement=g.YearMonth(1980, 6),
                    ),
                    PARAMS,
                )
            ),
        ),
        reasons.COMBINED_FAMILY_MAXIMUM: (
            "One child on retirement and survivor records",
            lambda: multiple_records(True),
        ),
        reasons.DEEMED_SPOUSE: (
            "Declared deemed spouse",
            lambda: _family(
                _retired(),
                [
                    g.Beneficiary(
                        "s",
                        g.Role.SPOUSE,
                        conditions={
                            g.BeneficiaryCondition.DEEMED_OR_PUTATIVE_SPOUSE
                        },
                    )
                ],
            ),
        ),
        reasons.PARENT_BENEFIT: (
            "Two potential parents; one own RIB 780 lies between 75% and 82.5% of PIA 1000",
            lambda: _family(
                _survivor(),
                [
                    g.Beneficiary(
                        "p",
                        g.Role.PARENT,
                        own_benefit=g.OwnBenefit(rib, F(780)),
                    ),
                    g.Beneficiary("p2", g.Role.PARENT),
                ],
            ),
        ),
        reasons.DISABLED_WIDOW_UNDER_60: (
            "DWB benefit month December 1983",
            lambda: _family(
                _survivor(),
                [g.Beneficiary("w", g.Role.DISABLED_WIDOW)],
                g.YearMonth(1983, 12),
            ),
        ),
        reasons.DIB_GUARANTEE_PIA: (
            "Declared DIB guarantee PIA",
            lambda: _family(
                _survivor(conditions={g.RecordCondition.DIB_GUARANTEE_PIA})
            ),
        ),
        reasons.DIB_AFTER_REDUCED_RIB: (
            "Own DIB reduced for prior reduced RIB",
            lambda: _family(
                _survivor(),
                [
                    g.Beneficiary(
                        "c",
                        g.Role.CHILD,
                        own_benefit=g.OwnBenefit(
                            dib, F(500), reduction_months=12
                        ),
                    )
                ],
            ),
        ),
        reasons.WORKERS_COMPENSATION_OFFSET: (
            "Disability record with declared workers compensation offset",
            lambda: _family(
                g.RecordState(
                    g.FamilyKind.DISABILITY,
                    F(1000),
                    F(1500),
                    conditions={g.RecordCondition.WORKERS_COMPENSATION_OFFSET},
                )
            ),
        ),
        reasons.GOVERNMENT_PENSION_OFFSET: (
            "Widow GPO before repeal in December 2023",
            lambda: _family(
                _survivor(),
                [
                    g.Beneficiary(
                        "w",
                        g.Role.WIDOW,
                        conditions={
                            g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET
                        },
                    )
                ],
                g.YearMonth(2023, 12),
            ),
        ),
        reasons.ADMINISTRATIVE_FINALITY: (
            "Declared finality protection",
            lambda: _family(
                _retired(
                    conditions={g.RecordCondition.ADMINISTRATIVE_FINALITY}
                )
            ),
        ),
        reasons.DUAL_ENTITLEMENT_SEQUENCE: (
            "Widow also entitled to own DIB",
            lambda: _family(
                _survivor(),
                [
                    g.Beneficiary(
                        "w",
                        g.Role.WIDOW,
                        own_benefit=g.OwnBenefit(dib, F(300)),
                        birth_year=1950,
                    )
                ],
            ),
        ),
        reasons.PARISI_AMBIGUOUS: (
            "Binding maximum with credited own RIB and a non-dual child",
            lambda: _family(
                _retired(),
                [
                    g.Beneficiary(
                        "s",
                        g.Role.SPOUSE,
                        own_benefit=g.OwnBenefit(
                            rib,
                            F(100),
                            delayed_credit_months=12,
                            birth_year=1950,
                        ),
                        own_benefit_first=True,
                        birth_year=1950,
                    ),
                    g.Beneficiary("c", g.Role.CHILD),
                ],
            ),
        ),
        reasons.PARISI_BEFORE_OCTOBER_1999: (
            "Binding mixed dual/non-dual family in September 1999",
            lambda: _family(
                _retired(),
                [
                    g.Beneficiary(
                        "s",
                        g.Role.SPOUSE,
                        own_benefit=g.OwnBenefit(rib, F(100)),
                        own_benefit_first=True,
                    ),
                    g.Beneficiary("c", g.Role.CHILD),
                ],
                g.YearMonth(1999, 9),
            ),
        ),
        reasons.INDEPENDENT_DIVORCED_SPOUSE: (
            "IEDS benefit month December 1984",
            lambda: _family(
                g.RecordState(
                    g.FamilyKind.RETIREMENT,
                    F(1000),
                    F(1500),
                    conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
                ),
                [g.Beneficiary("x", g.Role.DIVORCED_SPOUSE)],
                g.YearMonth(1984, 12),
            ),
        ),
        reasons.NON_AIME_FORMULA_PIA: (
            "Declared PIA outside the AIME formula",
            lambda: _family(
                _survivor(conditions={g.RecordCondition.NON_AIME_FORMULA_PIA})
            ),
        ),
        reasons.MULTIPLE_AUXILIARY_RECORDS: (
            "One person is divorced spouse and mother/father on two records",
            lambda: multiple_records(False),
        ),
        reasons.SAVINGS_CLAUSE: (
            "Protected total 1500 falls to 1499.90 after a PIA increase",
            lambda: _savings_witness(),
        ),
        reasons.SAVINGS_CLAUSE_HISTORY_UNKNOWN: (
            "Governed month begins with unknown prior entitlement months",
            lambda: _savings_witness(unknown=True),
        ),
        reasons.WIDOW_DRC_SAVINGS_CLAUSE: (
            "May 1978 survivor protected from widow deceased-worker DRCs",
            lambda: _family(_survivor(widow_drc_savings_clause=True)),
        ),
        reasons.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN: (
            "Direct survivor snapshot has widow DRCs and a child but lacks May 1978 attestation",
            lambda: _family(
                _survivor(widow_drc_savings_clause=None),
                [
                    g.Beneficiary(
                        "w",
                        g.Role.WIDOW,
                        original_benefit_basis=F(1100),
                        child_in_care=False,
                    ),
                    g.Beneficiary("c", g.Role.CHILD),
                ],
            ),
        ),
        reasons.WIDOW_CHILD_IN_CARE_UNKNOWN: (
            "A widow and an entitled child lack a current care attestation",
            lambda: _family(
                _survivor(),
                [
                    g.Beneficiary(
                        "w",
                        g.Role.WIDOW,
                        reduction_months=60,
                        reduction_period_months=60,
                        child_in_care=None,
                    ),
                    g.Beneficiary("c", g.Role.CHILD),
                ],
            ),
        ),
        reasons.DIVORCED_SPOUSE_CHILD_IN_CARE_UNKNOWN: (
            "A divorced spouse and an entitled child lack a current care attestation",
            lambda: _family(
                _retired(),
                [
                    g.Beneficiary(
                        "d",
                        g.Role.DIVORCED_SPOUSE,
                        first_entitlement_child_in_care=False,
                    ),
                    g.Beneficiary("c", g.Role.CHILD),
                ],
            ),
        ),
        reasons.DIVORCED_SPOUSE_CARE_HISTORY: (
            "An aged divorced spouse lacks first-entitlement care history that can change the amount",
            lambda: _family(
                _retired(),
                [
                    g.Beneficiary(
                        "d",
                        g.Role.DIVORCED_SPOUSE,
                        reduction_months=36,
                        child_in_care=False,
                    )
                ],
            ),
        ),
        reasons.DELAYED_CREDITS_BEFORE_1917: (
            "Own RIB has 12 credit months for a 1916 birth",
            lambda: _family(
                _retired(),
                [
                    g.Beneficiary(
                        "s",
                        g.Role.SPOUSE,
                        own_benefit=g.OwnBenefit(
                            rib,
                            F(300),
                            delayed_credit_months=12,
                            birth_year=1916,
                        ),
                        own_benefit_first=True,
                        birth_year=1916,
                    )
                ],
            ),
        ),
        reasons.OWN_RIB_HISTORY_BEFORE_1978: (
            "Spouse born in 1912 has own RIB PIA 1000 and RF1 but no pre-January-1978 reduction or PIA history",
            lambda: _family(
                _retired(F(2000), F(3000)),
                [
                    g.Beneficiary(
                        "spouse",
                        g.Role.SPOUSE,
                        own_benefit=g.OwnBenefit(
                            rib,
                            F(1000),
                            reduction_months=1,
                            birth_year=1912,
                        ),
                        own_benefit_first=True,
                        birth_year=1912,
                    )
                ],
                g.YearMonth(2023, 12),
            ),
        ),
        reasons.REDUCED_BENEFIT_HISTORY_BEFORE_1978: (
            "Spouse born in 1912 has RF1 on an unreduced 500 benefit but no pre-January-1978 money reduction or unreduced-rate history",
            lambda: _family(
                _retired(),
                [
                    g.Beneficiary(
                        "spouse",
                        g.Role.SPOUSE,
                        reduction_months=1,
                        birth_year=1912,
                    )
                ],
                g.YearMonth(2023, 12),
            ),
        ),
    }


def execute_refusal_witnesses() -> list[dict]:
    witnesses = refusal_witnesses()
    if set(witnesses) != set(g.UnsupportedReason):
        raise AssertionError("Every UnsupportedReason needs a named witness")
    results = []
    for expected, (description, compute) in sorted(
        witnesses.items(), key=lambda item: item[0].value
    ):
        try:
            compute()
        except g.FamilyConfigurationUnsupported as error:
            if error.reason is not expected:
                raise AssertionError((expected, error.reason)) from error
            results.append(
                {
                    "id": expected.value,
                    "description": description,
                    "status": "refused",
                    "reason": error.reason.value,
                }
            )
        else:
            raise AssertionError(f"Witness {expected.value} was not refused")
    return results


def _registry_summary(path: Path) -> dict:
    raw = path.read_bytes()
    registry = yaml.safe_load(raw)
    vocabulary = registry["tag_vocabulary"]
    counts = Counter({tag: 0 for tag in vocabulary})
    examples = registry["examples"]
    for example in examples:
        tags = example["tags"]
        if len(tags) != len(set(tags)) or not set(tags) <= set(vocabulary):
            raise ValueError("Registry tags must be unique vocabulary entries")
        counts.update(tags)
    try:
        relative = str(path.relative_to(ROOT))
    except ValueError:
        relative = path.name
    return {
        "file": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "examples": len(examples),
        "figures": sum(example["figure_count"] for example in examples),
        "counts_by_class": dict(sorted(counts.items())),
        "supported_classes": sorted(registry["supported_classes"]),
        "invented_only_classes": registry["invented_only_classes"],
    }


def build_report(registry_path: Path = DEFAULT_REGISTRY) -> dict:
    """Exhaustively classify each cell once, preserving every denominator."""
    statuses = Counter()
    refusals = Counter({reason.value: 0 for reason in g.UnsupportedReason})
    eras = {era: Counter() for era in PAYMENT_ERAS}
    for case in configurations():
        status, reason = classify_configuration(case)
        statuses[status] += 1
        eras[case.payment_era][status] += 1
        if reason is not None:
            refusals[reason] += 1
    witnesses = execute_refusal_witnesses()
    rows = sum(statuses.values())
    denominator = {
        "rows": rows,
        "supported": statuses["supported"],
        "refused": statuses["refused"],
        "invalid": statuses["invalid"],
    }
    return {
        "schema_version": 1,
        "verification_class": "statutory_conformance",
        "admitted_scope": "Gross benefits for supported invented configurations only; no population, behavioral, payment-timing or forecast claim.",
        "denominator_kind": "finite invented configuration lattice; no population data or population weights",
        "gross_benefits_version": g.GROSS_BENEFITS_VERSION,
        "lattice": {
            "definition": {
                "record_kinds": [kind.value for kind in g.FamilyKind],
                "role_enum_order": [role.value for role in ROLE_ORDER],
                "role_multiset_sizes": list(range(MAX_ROLE_MULTISET_SIZE + 1)),
                "role_multiset_count": len(role_multisets()),
                "dual_modes": list(DUAL_MODES),
                "reduction_months": list(REDUCTION_FLAGS),
                "widow_child_in_care": list(CHILD_IN_CARE_FLAGS),
                "divorced_spouse_child_in_care": list(CHILD_IN_CARE_FLAGS),
                "divorced_spouse_first_entitlement_child_in_care": False,
                "payment_eras": {
                    era: f"{month.year:04d}-{month.month:02d}"
                    for era, month in PAYMENT_ERAS.items()
                },
                "declared_conditions": [
                    {
                        "scope": scope,
                        "condition": condition.value if condition else None,
                    }
                    for scope, condition in declared_conditions()
                ],
                "focal_flags": "Dual entitlement, reduction months and a single beneficiary condition apply to the first beneficiary in Role enum multiset order. Every remaining beneficiary is unadjusted and not dually entitled. Empty multisets with any focal-beneficiary flag are invalid.",
                "dual_sequence": "Modes ending b select spouse method B; modes ending c select method C. Other roles retain G's supported sequencing or explicit refusal.",
                "fixed_money": {
                    "pia": "1000.00",
                    "retirement_and_disability_maximum": "1500.00",
                    "survivor_maximum": "1750.00",
                    "own_pia": "100.00",
                    "own_rib_reduction_months": 36,
                    "own_rib_credit_months": 12,
                },
                "birth_band": "1946 for the focal beneficiary and own RIB; widow reduction period 72 months. The living worker is unreduced, without credits; IEDS worker records have no worker payment.",
                "child_in_care": "Every widow(er), surviving divorced spouse, disabled widow(er) and divorced spouse receives the selected care input. None is unknown; False attests no care; entitled_child names the first child role on this record, or an absent-child sentinel if no child is present. Divorced spouses explicitly attest no entitled child in care at first entitlement. Unknown current care may refuse; naming an absent or non-entitled child is invalid. All three flag cells remain in the denominator even when the flag does not affect a role.",
                "snapshot_scope": "Standalone snapshots explicitly attest no protected May 1978 widow-DRC history unless the named condition is declared; monthly paths require SavingsClauseGuard. Refusal witnesses for unknown history, guarded histories and multiple records are counted separately.",
            },
            "denominator": denominator,
            "refused_by_reason": dict(sorted(refusals.items())),
            "by_payment_era": {
                era: {
                    "rows": sum(counts.values()),
                    "supported": counts["supported"],
                    "refused": counts["refused"],
                    "invalid": counts["invalid"],
                }
                for era, counts in eras.items()
            },
        },
        "supplemental_refusal_witnesses": {
            "scope": "Named invented witnesses outside the finite lattice; separate denominator, one valid refusal for every retained UnsupportedReason.",
            "denominator": {
                "rows": len(witnesses),
                "supported": 0,
                "refused": len(witnesses),
                "invalid": 0,
            },
            "refused_by_reason": {row["reason"]: 1 for row in witnesses},
            "witnesses": witnesses,
        },
        "registry": _registry_summary(registry_path),
    }


def report_bytes(report: dict) -> bytes:
    return (json.dumps(report, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    document = build_report(args.registry)
    args.output.write_bytes(report_bytes(document))
    print(
        f"Wrote {args.output}: {document['lattice']['denominator']['rows']} invented configurations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
