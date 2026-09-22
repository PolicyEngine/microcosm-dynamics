"""Validation-only diagnostic for the SSDI entitlement component (Track A A4).

Projects a SYNTHETIC opening population from December 2008 through 2023
with the real adapters in :mod:`populace_dynamics.engine.di_entitlement`
and compares the projected disabled-worker stock with SSA's 2023 DI Annual
Statistical Report (``data/external/di_asr_2023``: Table 19 stock and age
distribution by sex, Table 35 worker awards, Table 49 worker terminations).

Governance (critical-path plan section 4):

* This is a reported diagnostic, not a fitting target.  No rate is tuned to
  these comparisons; the rates are fit on <=2008 data only.
* The opening population is synthetic: Census Vintage 2008 July 1, 2008
  resident population by single year of age and sex, with the December 2008
  disabled-worker stock from ASR 2008 Table 20 spread evenly over the single
  ages of each age group.  It is not the PSID cohort and not a Track A run.
  It is closed: no immigration and no births after 2008.
* Population mortality is the NCHS 2000 life table held constant (no
  improvement), the <=2008 table in the repository, as a single-year-of-age
  ``AgeSexMortalityModel``.  The default multiplier takes its NCHS 2000 base
  at that model's single-age bands, so below age 100 disabled-worker
  mortality equals the Actuarial Study No. 118 (1996-2000) level.  The
  NCHS table is all-person mortality, so by default the non-DI-origin
  records' probabilities are scaled within each single age and sex to keep
  the expected (weighted) deaths at the NCHS level; the
  ``non_di_population_total`` variant keeps them at the NCHS level instead.
* No COLA statistic, benefit, or DYNASIM comparator value is computed.

The adapters run through their no-registry (batch-generator) path with fixed
per-year seeds; the registry path is exercised by the unit tests.

Run from the repository root (needs the policyengine-us checkout for the
statutory FRA schedule)::

    .venv/bin/python scripts/validate_di_entitlement_asr2023.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.engine.di_entitlement import (  # noqa: E402
    apply_di_aware_mortality,
    apply_di_entitlement,
    di_prevalence,
    di_stock_flow,
    fra_schedule_from_parameters,
    prepare_opening_di_state,
)
from populace_dynamics.engine.di_entitlement_rates import (  # noqa: E402
    DEFAULT_INPUTS_PATH,
    NCHS_2000_PATH,
    SEXES,
    DIEntitlementSpec,
    load_di_entitlement_rates,
    pending_decisions,
)
from populace_dynamics.engine.loop import PeriodContext  # noqa: E402
from populace_dynamics.engine.steps import (  # noqa: E402
    AgeSexMortalityModel,
    advance_age,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

ASR_2023_PATH = ROOT / "data" / "external" / "di_asr_2023" / "tables.json"
OUT_PATH = ROOT / "runs" / "di_entitlement_asr2023_validation_v1.json"

SCHEMA_VERSION = "di_entitlement_asr2023_validation.v1"
OPENING_YEAR = 2008
END_YEAR = 2023
SEED_BASE = 5200
NON_ENTITLED_RECORDS_PER_CELL = 2000
ENTITLED_RECORDS_PER_CELL = 400
TABLE19_GROUPS = (
    ("Under 30", 0, 29),
    ("30–34", 30, 34),
    ("35–39", 35, 39),
    ("40–44", 40, 44),
    ("45–49", 45, 49),
    ("50–54", 50, 54),
    ("55–59", 55, 59),
    ("60–FRA", 60, None),
)
STOCK_GROUP_AGES = {
    "Under 25": (18, 24),
    "25–29": (25, 29),
    "30–34": (30, 34),
    "35–39": (35, 39),
    "40–44": (40, 44),
    "45–49": (45, 49),
    "50–54": (50, 54),
    "55–59": (55, 59),
    "60–64": (60, 64),
    "65–FRA": (65, 65),
}
VARIANTS = {
    "default": DIEntitlementSpec(),
    "explicit_death_asr2008_level": DIEntitlementSpec(
        death_mode="explicit", death_level="asr_fitted"
    ),
    "fit_year_2007": DIEntitlementSpec(fit_year="2007"),
    "non_di_population_total": DIEntitlementSpec(
        non_di_mortality="population_total"
    ),
}
LABEL = (
    "VALIDATION-ONLY DIAGNOSTIC on a SYNTHETIC opening population (Census "
    "V2008 July 2008 population x ASR 2008 Table 20 disabled-worker stock; "
    "not PSID, not Track A). Not a fitting target: no rate was tuned to "
    "these comparisons. No COLA statistic or DYNASIM comparator value is "
    "computed or read."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _number(text: str) -> float | None:
    cleaned = text.strip().replace(",", "")
    # "a": ages 30-34 were grouped with 35-39 before 1996.
    if cleaned in {"", "--", ". . .", "a"}:
        return None
    return float(cleaned)


def load_asr_2023() -> dict[str, Any]:
    """Parse the validation-only 2023 ASR tables into year-keyed series."""
    tables = json.loads(ASR_2023_PATH.read_text(encoding="utf-8"))
    lines = tables["Table 19"]["tsv"].split("\n")
    section = None
    table19: dict[str, dict[int, dict[str, Any]]] = {
        "all": {},
        "male": {},
        "female": {},
    }
    names = {
        "All disabled workers b": "all",
        "Men": "male",
        "Women": "female",
    }
    for line in lines:
        cells = line.split("\t")
        if cells[0] == "" and len(cells) > 1 and cells[1] in names:
            section = names[cells[1]]
            continue
        if section and cells[0].isdigit() and len(cells[0]) == 4:
            table19[section][int(cells[0])] = {
                "number_thousands": _number(cells[1]),
                "percent": [_number(cell) for cell in cells[3:11]],
            }
    awards = {}
    for line in tables["Table 35"]["tsv"].split("\n"):
        cells = line.split("\t")
        if cells[0].isdigit() and len(cells[0]) == 4:
            awards[int(cells[0])] = _number(cells[2])
    terminations = {}
    for line in tables["Table 49"]["tsv"].split("\n"):
        cells = line.split("\t")
        if cells[0].isdigit() and len(cells[0]) == 4:
            terminations[int(cells[0])] = _number(cells[3])
    return {
        "table19": table19,
        "awards_workers": awards,
        "terminations_workers": terminations,
    }


def nchs_2000_mortality() -> AgeSexMortalityModel:
    life = json.loads(NCHS_2000_PATH.read_text(encoding="utf-8"))
    bands = tuple((age, age) for age in range(100)) + ((100, 120),)
    probability = {}
    for sex in SEXES:
        rows = {
            int(row["age"]): float(row["qx"]) for row in life["tables"][sex]
        }
        for lower, upper in bands:
            label = AgeSexMortalityModel.band_label(lower, upper)
            probability[(label, sex)] = rows[lower]
    return AgeSexMortalityModel(bands=bands, probability=probability)


def synthetic_opening_population(inputs: dict[str, Any]) -> pd.DataFrame:
    """SYNTHETIC December 2008 population (see module docstring)."""
    census = inputs["census_resident_population_july1"]["2008"]
    stock_table = inputs["asr"]["2008"]["stock_workers_december"]
    frames = []
    next_id = 1
    for sex in SEXES:
        stock_by_age = np.zeros(101)
        for label, count in zip(
            stock_table["age_groups"], stock_table[sex], strict=True
        ):
            lower, upper = STOCK_GROUP_AGES[label]
            stock_by_age[lower : upper + 1] = count / (upper - lower + 1)
        for age in census["ages"]:
            population = float(census[sex][age])
            entitled = float(stock_by_age[age])
            cells = [
                (False, population - entitled, NON_ENTITLED_RECORDS_PER_CELL)
            ]
            if entitled > 0:
                cells.append((True, entitled, ENTITLED_RECORDS_PER_CELL))
            for is_entitled, total, records in cells:
                ids = np.arange(next_id, next_id + records, dtype=np.int64)
                next_id += records
                frames.append(
                    pd.DataFrame(
                        {
                            "person_id": ids,
                            "year": OPENING_YEAR,
                            "sex": sex,
                            "birth_year": OPENING_YEAR - age,
                            "age": age,
                            "weight": total / records,
                            "di_entitled": is_entitled,
                        }
                    )
                )
    return pd.concat(frames, ignore_index=True)


def _slice_summary(
    frame: pd.DataFrame, year: int, flow: dict[str, Any] | None
) -> dict[str, Any]:
    prevalence = di_prevalence(
        frame, age_groups=TABLE19_GROUPS, weight_column="weight"
    )
    out: dict[str, Any] = {"year": year, "stock_thousands": {}, "percent": {}}
    for sex in SEXES:
        rows = prevalence[prevalence["sex"] == sex]
        out["stock_thousands"][sex] = float(rows["weighted"].sum()) / 1000.0
        out["percent"][sex] = [
            100.0 * float(value) for value in rows["share_of_sex_stock"]
        ]
    out["stock_thousands"]["all"] = sum(
        out["stock_thousands"][sex] for sex in SEXES
    )
    if flow is not None:
        out["flows_thousands"] = {
            name: flow[f"{name}_weighted"] / 1000.0
            for name in (
                "awards",
                "deaths",
                "recoveries",
                "conversions",
                "stock_start",
                "stock_end",
            )
        }
    return out


def run_variant(
    spec: DIEntitlementSpec,
    opening: pd.DataFrame,
    fra_schedule: Any,
    mortality: AgeSexMortalityModel,
) -> dict[str, Any]:
    rates = load_di_entitlement_rates(spec)
    current = prepare_opening_di_state(
        opening, rates=rates, fra_schedule=fra_schedule
    )
    summaries = [_slice_summary(current, OPENING_YEAR, None)]
    death_log: dict[int, pd.DataFrame] = {}
    for period, year in enumerate(
        range(OPENING_YEAR + 1, END_YEAR + 1), start=1
    ):
        context = PeriodContext(period, year, 0, {})
        previous = current
        current = apply_di_aware_mortality(
            current,
            context,
            np.random.default_rng([SEED_BASE, year, 1]),
            population_model=mortality,
            rates=rates,
            death_log=death_log,
            weight_column="weight",
        )
        current = advance_age(current, context, np.random.default_rng(0))
        current = apply_di_entitlement(
            current,
            context,
            np.random.default_rng([SEED_BASE, year, 5]),
            rates=rates,
            fra_schedule=fra_schedule,
        )
        flow = di_stock_flow(
            [previous, current], weight_column="weight", death_log=death_log
        ).iloc[0]
        summaries.append(_slice_summary(current, year, flow.to_dict()))
    return {
        "spec": spec.as_dict(),
        "rates": rates.summary(),
        "years": summaries,
    }


def compare(
    variant: dict[str, Any], asr: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = []
    for summary in variant["years"]:
        year = summary["year"]
        row: dict[str, Any] = {"year": year}
        for sex, key in (("male", "male"), ("female", "female")):
            published = asr["table19"][key].get(year)
            if published is None:
                continue
            model_stock = summary["stock_thousands"][sex]
            row[f"{sex}_stock_model_thousands"] = model_stock
            row[f"{sex}_stock_asr_thousands"] = published["number_thousands"]
            row[f"{sex}_stock_ratio"] = (
                model_stock / published["number_thousands"]
            )
            gaps = [
                model - reference
                for model, reference in zip(
                    summary["percent"][sex], published["percent"], strict=True
                )
            ]
            row[f"{sex}_distribution_gap_pp"] = gaps
            row[f"{sex}_distribution_mean_abs_gap_pp"] = float(
                np.mean(np.abs(gaps))
            )
        flows = summary.get("flows_thousands")
        if flows is not None:
            awards = asr["awards_workers"].get(year)
            terminations = asr["terminations_workers"].get(year)
            row["awards_model_thousands"] = flows["awards"]
            row["awards_asr_thousands"] = (
                None if awards is None else awards / 1000.0
            )
            model_terminations = (
                flows["deaths"] + flows["recoveries"] + flows["conversions"]
            )
            row["terminations_model_thousands"] = model_terminations
            row["terminations_asr_thousands"] = (
                None if terminations is None else terminations / 1000.0
            )
        rows.append(row)
    return rows


def main() -> int:
    started = time.time()
    inputs = json.loads(DEFAULT_INPUTS_PATH.read_text(encoding="utf-8"))
    params = load_ssa_parameters()
    fra_schedule = fra_schedule_from_parameters(params)
    mortality = nchs_2000_mortality()
    opening = synthetic_opening_population(inputs)
    asr = load_asr_2023()
    variants = {}
    for name, spec in VARIANTS.items():
        result = run_variant(spec, opening, fra_schedule, mortality)
        result["comparison"] = compare(result, asr)
        variants[name] = result
        print(f"{name}: done ({time.time() - started:.0f}s)")
    stock = inputs["asr"]["2008"]["stock_workers_december"]["totals"]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "label": LABEL,
        "validation_only": True,
        "fitting_target": False,
        "computes_cola_statistic": False,
        "reads_comparator_values": False,
        "opening_population": {
            "kind": "SYNTHETIC",
            "year": OPENING_YEAR,
            "construction": (
                "Census V2008 July 1, 2008 resident population by single "
                "age 0-100 and sex; ASR 2008 Table 20 December 2008 "
                "disabled-worker stock spread evenly over each group's "
                "single ages (Under 25 -> 18-24; 65-FRA -> 65); "
                f"{NON_ENTITLED_RECORDS_PER_CELL} non-entitled and "
                f"{ENTITLED_RECORDS_PER_CELL} entitled weighted records per "
                "age-sex cell; closed (no births or immigration after 2008)"
            ),
            "records": int(len(opening)),
            "asr2008_table20_stock": stock,
        },
        "population_mortality": (
            "NCHS United States Life Tables, 2000 (single years 0-99, age "
            "100+ as one band), constant over 2009-2023; all-person "
            "mortality, netted of DI-origin deaths within each age-sex cell "
            "except in the non_di_population_total variant"
        ),
        "fra_schedule": {
            "source": "SSAParameters.fra_months (policyengine-us tree)",
            "policyengine_us_revision": params.pe_us_revision,
        },
        "rng": {
            "path": "no-registry batch generators",
            "mortality_seed": [SEED_BASE, "year", 1],
            "disability_seed": [SEED_BASE, "year", 5],
        },
        "comparison_source": {
            "path": "data/external/di_asr_2023/tables.json",
            "sha256": _sha256(ASR_2023_PATH),
            "tables": ["Table 19", "Table 35", "Table 49"],
            "role": "validation only",
        },
        "inputs": {
            "di_asr_2008_tables_sha256": _sha256(DEFAULT_INPUTS_PATH),
            "nchs_2000_sha256": _sha256(NCHS_2000_PATH),
        },
        "age_groups": [label for label, _, _ in TABLE19_GROUPS],
        "age_definition": "year - birth_year at the end of the year",
        "concept_deltas": [
            "model stock is entitled disabled workers; ASR counts workers "
            "in current-payment status (suspensions excluded)",
            "the synthetic population is closed, so it omits post-2008 "
            "immigrants",
            "rates are held at their fit-year level; no business-cycle or "
            "administrative variation after 2008 is modeled",
            "model deaths start the year after award; entitlement often "
            "precedes the award",
            "ASR 'other' terminations and elected reduced retirement are "
            "not modeled",
            "with one assumed birth month (July) every member of a birth "
            "cohort converts in the same calendar year; the 1956 cohort "
            "(FRA 66y4m) then converts in 2022 and the 1957 cohort (66y6m) "
            "in 2024, so 2023 has no model conversions, while in fact parts "
            "of both cohorts convert in 2023 (the FRA-67 cohorts that matter "
            "in 2030 are unaffected)",
        ],
        "pending_decisions": pending_decisions(),
        "variants": variants,
    }
    OUT_PATH.write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {OUT_PATH.relative_to(ROOT)} in {time.time() - started:.0f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
