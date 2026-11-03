"""Statutory conformance: exact R2/R3 cross-head invented-input diagnostic.

No population, behavioral, or forecast claim. Compare every declared field
and type of 240 supported R2 ledgers and their same-record R3 RIB results.
Six separate binding survivor cases measure coverage movement. The baseline
is an existing local source tree; this script never fetches or edits it.

Run with PYTHONPATH=src:. python scripts/track_b_r2_cross_head.py
--baseline-root <local-tree> --output <report.json>.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from datetime import date
from enum import Enum
from fractions import Fraction as F
from pathlib import Path

from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import BenefitType as T
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.track_b_gross_benefit_support import ssa_params


def encode(value):
    if dataclasses.is_dataclass(value):
        return {
            "type": type(value).__name__,
            **{
                f.name: encode(getattr(value, f.name))
                for f in dataclasses.fields(value)
            },
        }
    if isinstance(value, F):
        return [value.numerator, value.denominator]
    if isinstance(value, Enum):
        return [type(value).__name__, value.value]
    if isinstance(value, Mapping):
        return {str(k): encode(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [encode(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(
            (encode(v) for v in value),
            key=lambda x: json.dumps(x, sort_keys=True),
        )
    if isinstance(value, date):
        return value.isoformat()
    return value


def _dump(path):
    params = load_ret_parameters()
    ssa = ssa_params()
    months = frozenset(range(1, 13))
    exempt = params.for_year(2026).lower_exempt_amount.value
    random_source = random.Random(53014)

    def person(key, rate, original, kind, excess=0, estimate=None, fra=None):
        def work(n):
            annual = exempt + 2 * n if n else 0
            return r.WorkEarnings((F(annual),) + (F(0),) * 11)

        return r.RETBeneficiary(
            key,
            (kind,) * 12,
            months,
            (F(rate),) * 12,
            (F(original),) * 12,
            earnings=work(excess),
            estimated_earnings=None if estimate is None else work(estimate),
            fra_month=fra,
        )

    def evaluate(record):
        try:
            ledger = r.apply_ret_year(record, params)
        except g.FamilyConfigurationUnsupported as error:
            return {"refusal": error.reason.value}
        if record.kind is r.RecordKind.DECEASED:
            return {"ledger": encode(ledger)}
        credits = frozenset(
            g.YearMonth(2026, m) for m in ledger.crediting_months[record.nh_id]
        )
        arf = a.apply_arf(
            a.ARFClaim(
                a.ARFBenefitKind.RIB,
                date(1960, 1, 2),
                g.YearMonth(2022, 1),
                F(1300),
                full_work_deduction_months=credits,
            ),
            payment_month=g.YearMonth(2027, 1),
            params=ssa,
        )
        return {"ledger": encode(ledger), "arf": encode(arf)}

    stable = []
    for index in range(240):
        nh_rate = F(random_source.randint(1, 12000), 10)
        people = [
            person(
                "nh",
                nh_rate,
                nh_rate,
                T.RIB,
                random_source.randint(0, 15000),
                random_source.randint(0, 15000),
                fra=0 if index % 11 == 0 else None,
            )
        ]
        for aux in range(index % 4):
            original = F(random_source.randint(1, 6000), 10)
            rate = F(random_source.randint(0, int(original * 10)), 10)
            kind = (T.SPOUSE, T.CHILD, T.CDB, T.DIVORCED_SPOUSE)[
                (index + aux) % 4
            ]
            people.append(
                person(
                    f"a{aux}",
                    rate,
                    original,
                    kind,
                    random_source.randint(0, 3000),
                    random_source.randint(0, 3000),
                )
            )
        stable.append(
            evaluate(r.RecordYear(2026, "nh", beneficiaries=tuple(people)))
        )

    transitions = []
    for excess in (1, 60, 99, 100, 555, 1188):
        state = g.RecordState(
            g.FamilyKind.SURVIVOR, F("213.10"), F(396), eligibility_year=2026
        )
        beneficiaries = (g.Beneficiary("e", g.Role.MOTHER_FATHER),) + tuple(
            g.Beneficiary(k, g.Role.CHILD) for k in ("c1", "c2", "c3")
        )
        family = g.family_benefits(
            state,
            beneficiaries,
            payment_month=g.YearMonth(2026, 1),
            params=ssa,
            standalone=True,
        )
        rows = {b.beneficiary_id: b for b in family.beneficiaries}
        people = tuple(
            person(
                k,
                rows[k].auxiliary_payable,
                rows[k].original_benefit,
                T.MOTHER_FATHER if k == "e" else T.CHILD,
                excess if k == "c3" else 0,
            )
            for k in rows
        )
        keywords = {}
        if hasattr(r, "RETFamilyMonth"):
            context = r.RETFamilyMonth(
                state, beneficiaries, ssa, {k: "one" for k in rows}
            )
            keywords["family_months"] = {m: context for m in months}
        record = r.RecordYear(
            2026,
            "nh",
            r.RecordKind.DECEASED,
            people,
            family_maximum_binding_months=months,
            **keywords,
        )
        transitions.append(evaluate(record))
    path.write_text(
        json.dumps(
            {"stable": stable, "transitions": transitions},
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dump", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.dump is not None:
        expected = Path(os.environ["TRACK_B_CROSS_HEAD_ROOT"])
        assert Path(r.__file__).is_relative_to(expected / "src")
        _dump(args.dump)
        return
    if args.baseline_root is None:
        parser.error("--baseline-root is required")
    baseline = args.baseline_root.resolve()
    root = Path(__file__).resolve().parents[1]
    script = Path(__file__).resolve()
    with tempfile.TemporaryDirectory(
        prefix=".trackb-r2-cross-head-", dir=root
    ) as temporary:
        values = {}
        for name, source_root in (("baseline", baseline), ("head", root)):
            destination = Path(temporary) / f"{name}.json"
            environment = {
                **os.environ,
                "PYTHONPATH": f"{source_root / 'src'}:{source_root}",
                "POPULACE_DYNAMICS_PSID_DIR": str(root / ".no-real-data"),
                "POPULACE_DYNAMICS_EPUF_DIR": str(root / ".no-real-data"),
                "OMP_NUM_THREADS": "1",
                "POLARS_MAX_THREADS": "1",
                "TRACK_B_CROSS_HEAD_ROOT": str(source_root),
            }
            subprocess.run(
                [sys.executable, str(script), "--dump", str(destination)],
                cwd=source_root,
                env=environment,
                check=True,
            )
            values[name] = json.loads(destination.read_text())

    def canonical(value):
        return json.dumps(
            value, sort_keys=True, separators=(",", ":")
        ).encode()

    before = canonical(values["baseline"]["stable"])
    after = canonical(values["head"]["stable"])
    if before != after:
        raise AssertionError(
            "Previously supported R2/R3 declared output bytes differ"
        )
    transitions = {}
    for name, document in values.items():
        rows = document["transitions"]
        refused = {}
        for row in rows:
            if "refusal" in row:
                refused[row["refusal"]] = refused.get(row["refusal"], 0) + 1
        transitions[name] = {
            "rows": len(rows),
            "supported": sum("ledger" in row for row in rows),
            "refused_by_reason": refused,
        }
    report = {
        "verification_class": "statutory conformance",
        "scope": "invented cases only; no population, behavioral or forecast claim",
        "seed": 53014,
        "r2_stable_rows": len(values["head"]["stable"]),
        "r3_stable_rows": sum(
            "arf" in row for row in values["head"]["stable"]
        ),
        "identical_declared_output_bytes": True,
        "stable_sha256": hashlib.sha256(after).hexdigest(),
        "transitions": transitions,
        "transition_rows": [
            {
                "id": f"binding_survivor_own_excess_{excess}",
                "own_excess": excess,
                "baseline": (
                    "supported"
                    if "ledger" in before_row
                    else before_row["refusal"]
                ),
                "head": (
                    "supported"
                    if "ledger" in after_row
                    else after_row["refusal"]
                ),
            }
            for excess, before_row, after_row in zip(
                (1, 60, 99, 100, 555, 1188),
                values["baseline"]["transitions"],
                values["head"]["transitions"],
                strict=True,
            )
        ],
    }
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
