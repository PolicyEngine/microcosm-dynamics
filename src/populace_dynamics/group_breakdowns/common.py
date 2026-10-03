"""Reproduction gate and G1/G2/G3 composition for exercises 1 and 3.

Sources: the frozen Track A and FRA68 runners, and the category definitions
and citations in ``estimates.group_breakdown.MINT8_SCHEME``. No PSID reader
is called here except through G1's cohort loader. No measure or statistic
is reimplemented: G2 supplies measures and G3 supplies assignments/cells.

Invariants: every frozen result field matches before any attribute loader
or lifetime calculation runs; joins preserve unique (draw, person_id)
keys; lifetime categories are fixed on the opening cohort within birth
decade; the MINT variant contains current-law recipients aged 60+ only.
Missing income, marriage history or sourced interest rates are unavailable,
never invented zeroes. The caller writes only after this function returns.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

import pandas as pd

from populace_dynamics.cohorts import group_attributes as g1
from populace_dynamics.cola_track_a.config import REGISTERED_ROWS
from populace_dynamics.estimates import group_breakdown as g3
from populace_dynamics.estimates import lifetime_measures as g2
from populace_dynamics.estimates.cola_age_profile import ColaAgeProfileConfig

POST_HOC_LABELS = (
    "registered, one-shot, post hoc, not blind",
    "report-only",
)
INVENTED_HEADER = "INVENTED DATA - NOT A COMPARISON"
INCOME_REASON = (
    "The closed projection has no household income or official poverty "
    "measure; poverty status and household income quintiles are not computed."
)


class ReproductionMismatch(ValueError):
    """Frozen parent reproduction failed; no group cells may be computed."""


@dataclass(frozen=True)
class ProjectionReplay:
    """Frozen result plus in-memory rows and final states, before grouping."""

    exercise: str
    result: Mapping[str, Any]
    benefit_rows: Mapping[str, pd.DataFrame]
    states: Mapping[int, pd.DataFrame]
    retention_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "retention_sha256", _retention_digest(self))


@dataclass(frozen=True)
class LifetimeOptions:
    """Sourced G2 inputs; marriage history is resolved only after the gate.

    The loader returns (episodes, history person ids) for an anchor wave.
    Absent history is explicitly unavailable, rather than never-married.
    """

    rates: Any = None
    interest: Any = None
    marriage_episode_loader: (
        Callable[[int], tuple[pd.DataFrame, tuple[int, ...]]] | None
    ) = None


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _retention_digest(replay: ProjectionReplay) -> str:
    """Seal retained content, including nested component dicts and keys."""
    digest = hashlib.sha256(replay.exercise.encode())
    for name, frames in (
        ("benefits", replay.benefit_rows),
        ("states", replay.states),
    ):
        for key in sorted(frames, key=str):
            frame = frames[key]
            digest.update(_canonical((name, key, list(frame.columns))))
            digest.update(_canonical([str(dtype) for dtype in frame.dtypes]))
            digest.update(
                frame.to_csv(index=False, lineterminator="\n").encode()
            )
    return digest.hexdigest()


def _first_difference(actual: Any, expected: Any, path: str) -> str | None:
    if isinstance(actual, Mapping) and isinstance(expected, Mapping):
        if set(actual) != set(expected):
            return path + ".keys"
        for key in sorted(actual):
            difference = _first_difference(
                actual[key], expected[key], f"{path}.{key}"
            )
            if difference:
                return difference
        return None
    if isinstance(actual, (list, tuple)) and isinstance(
        expected, (list, tuple)
    ):
        if len(actual) != len(expected):
            return path + ".length"
        for index, (left, right) in enumerate(
            zip(actual, expected, strict=True)
        ):
            difference = _first_difference(left, right, f"{path}[{index}]")
            if difference:
                return difference
        return None
    return None if _canonical(actual) == _canonical(expected) else path


def verify_reproduction(
    replay: ProjectionReplay, parent: Mapping[str, Any]
) -> dict[str, Any]:
    """Require exact JSON values for every recomputed frozen result field.

    Only the parent's entry-script wrapper (run times, environment, etc.)
    lies outside the frozen runner's returned result. No floating tolerance
    is used; differing summation requires a new reviewed convention.
    Failure identifies a path, without printing any outcome value.
    """

    if not replay.result.get("rows") or not replay.result.get("draws"):
        raise ReproductionMismatch("replay lacks frozen rows or draws")
    absent = set(replay.result) - set(parent)
    if absent:
        raise ReproductionMismatch(f"parent lacks fields {sorted(absent)}")
    expected = {key: parent[key] for key in replay.result}
    difference = _first_difference(replay.result, expected, "result")
    if difference:
        raise ReproductionMismatch(
            f"frozen reproduction mismatch at {difference}"
        )
    row_ids = set(replay.result["rows"])
    if set(replay.benefit_rows) != row_ids:
        raise ReproductionMismatch(
            "retained rows differ from frozen row manifest"
        )
    if _retention_digest(replay) != replay.retention_sha256:
        raise ReproductionMismatch(
            "retained projection frames changed after replay"
        )
    return {
        "identical": True,
        "comparison": "exact canonical JSON values; no floating tolerance",
        "absolute_tolerance": 0.0,
        "relative_tolerance": 0.0,
        "verified_result_fields": sorted(replay.result),
        "verified_rows": sorted(row_ids),
        "verified_payload_sha256": hashlib.sha256(
            _canonical(expected)
        ).hexdigest(),
        "ordering": "all frozen fields verified before G1/G2/G3 grouping",
        "retention_sha256": replay.retention_sha256,
    }


def benefit_type(components: Mapping[str, Mapping[str, float]]) -> str | None:
    """Map baseline components to G3's four MINT benefit types.

    A positive aged/disabled widow component takes the widow row, including
    own-worker dual entitlement; otherwise a positive spouse excess takes
    the spousal row. Worker-only means exactly one worker kind. A baseline
    nonrecipient is unclassified. Concurrent widow/spouse or two worker
    kinds are refused, since the frozen calculator should not emit them.
    """

    allowed = {
        "retired_worker",
        "disabled_worker",
        "spouse",
        "aged_widow",
        "disabled_widow",
    }
    if set(components) - allowed:
        raise ValueError("unknown benefit component")
    if any(
        isinstance(amounts["base"], bool)
        or not math.isfinite(amounts["base"])
        or amounts["base"] < 0
        for amounts in components.values()
    ):
        raise ValueError(
            "baseline components must be finite nonnegative amounts"
        )
    active = {
        name for name, amounts in components.items() if amounts["base"] > 0
    }
    widow = bool(active & {"aged_widow", "disabled_widow"})
    if widow and "spouse" in active:
        raise ValueError(
            "concurrent widow and spouse benefits have no mapping"
        )
    if {"retired_worker", "disabled_worker"} <= active:
        raise ValueError("concurrent worker benefit kinds have no mapping")
    if widow:
        return "widower"
    if "spouse" in active:
        return "spousal"
    if "retired_worker" in active:
        return "retired_worker_only"
    if "disabled_worker" in active:
        return "disabled_worker_only"
    return None


def _label_codes(series: pd.Series, dimension: g3.Dimension) -> pd.Series:
    codes = {category.label: category.key for category in dimension.categories}
    unknown = set(series.dropna()) - set(codes)
    if unknown:
        raise ValueError(f"G1 labels outside G3 {dimension.key} scheme")
    return series.map(codes)


def _fixed_lifetime_dimensions() -> tuple[g3.Dimension, ...]:
    return tuple(
        replace(
            dimension,
            kind=g3.CATEGORICAL,
            categories=tuple(
                replace(category, codes=(category.key,), rank=None)
                for category in dimension.categories
            ),
            notes=(*dimension.notes, "G3 categories fixed on opening cohort"),
        )
        for dimension in g3.LIFETIME_DIMENSIONS
    )


def _lifetime_side(
    cohort: Any, params: Any, options: LifetimeOptions
) -> tuple[pd.DataFrame, dict[str, Any]]:
    persons = cohort.persons[["person_id", "birth_year", "weight"]].copy()
    careers = pd.DataFrame(
        [
            (pid, year, earnings)
            for pid, history in cohort.careers.items()
            for year, earnings in history.items()
            if year <= cohort.start_year
        ],
        columns=["person_id", "year", "earnings"],
    )
    rates = options.rates
    if rates is None:
        rates = g2.load_oasdi_tax_rates(
            basis=g2.TaxRateBasis.EMPLOYEE_EMPLOYER_PAID
        )
    interest = options.interest
    if interest is None:
        interest = g2.load_trust_fund_interest_rates()
    aime = g2.initial_aime_at_62(
        careers,
        persons,
        params,
        analysis_year=cohort.start_year,
        convention=g2.AIME_CONVENTIONS["mint8_initial_aime"],
    )
    own = g2.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        params,
        shared=False,
        rates=rates,
        interest=interest,
        missing_rate=g2.MissingRatePolicy.NOT_COMPUTED,
    )
    measures = {
        "initial_aime_quintile": (aime, "aime"),
        "lifetime_payroll_tax_quintile": (own, "pv_at_62"),
    }
    provenance: dict[str, Any] = {}
    absent_history_ids: set[int] = set()
    shared_key = "lifetime_payroll_tax_quintile_shared"
    if options.marriage_episode_loader is None:
        persons[shared_key] = float("nan")
        provenance[shared_key] = {
            "status": "not computed",
            "reason": "marriage history not supplied",
        }
    else:
        episodes, history_ids = options.marriage_episode_loader(
            cohort.anchor_wave
        )
        shared = g2.lifetime_payroll_tax_pv_at_62(
            careers,
            persons,
            params,
            shared=True,
            rates=rates,
            interest=interest,
            marriage_episodes=episodes,
            marriage_history_person_ids=history_ids,
            missing_spouse=g2.MissingSpousePolicy.NOT_COMPUTED,
            missing_rate=g2.MissingRatePolicy.NOT_COMPUTED,
        )
        # Do not mutate G2's measure frame/provenance. Its explicit history
        # coverage flag governs which values this adapter may classify.
        absent_history_ids = set(persons["person_id"]) - set(history_ids)
        measures[shared_key] = (shared, "pv_at_62")
    for key, (measure, column) in measures.items():
        side = measure.frame[["person_id", column]].rename(
            columns={column: key}
        )
        if key == shared_key:
            side.loc[side["person_id"].isin(absent_history_ids), key] = float(
                "nan"
            )
        persons = persons.merge(side, on="person_id", validate="one_to_one")
        provenance[key] = {
            "measure": measure.measure,
            "provenance": measure.provenance,
            "status_counts": measure.frame["status"].value_counts().to_dict(),
            "unavailable_reasons": measure.frame["reason"]
            .dropna()
            .value_counts()
            .to_dict(),
        }
        if key == shared_key:
            provenance[key]["adapter_unavailable_marriage_history"] = len(
                absent_history_ids
            )
    persons["birth_cohort"] = g2.ten_year_birth_cohort(persons["birth_year"])
    scheme = g3.derive_scheme(
        g3.MINT8_COHORT_SCHEME,
        scheme_id="projection_opening_lifetime",
        title="Opening-cohort lifetime categories",
        drop=("sex", "race_ethnicity", "country_of_birth", "education"),
    )
    assignment = g3.assign_groups(
        persons,
        scheme,
        {d.key: d.key for d in g3.LIFETIME_DIMENSIONS},
        key_columns=("person_id",),
        quintile_partition=("birth_cohort",),
    )
    for dimension in g3.LIFETIME_DIMENSIONS:
        codes = assignment.long.loc[
            assignment.long["dimension"] == dimension.key, "category"
        ].reset_index(drop=True)
        persons[dimension.key] = codes.where(codes != g3.UNCLASSIFIED, None)
    provenance["quintiles"] = assignment.as_dict()
    provenance["history_window"] = (
        f"careers through opening year {cohort.start_year}"
    )
    return (
        persons.drop(columns=["birth_year", "weight", "birth_cohort"]),
        provenance,
    )


def run_group_breakdown(
    replay: ProjectionReplay,
    parent: Mapping[str, Any],
    *,
    inputs: Any,
    config: Any,
    attribute_loader: Callable[..., g1.GroupAttributes] | None = None,
    lifetime_options: LifetimeOptions | None = None,
    parent_sha256: str | None = None,
    registration_pointer: str | None = None,
) -> dict[str, Any]:
    """Verify the entire replay, then join side frames and call G3.

    Returns a JSON-safe report with no person rows. The registered entry
    point handles exclusive writing; this function performs no writes.
    """

    identity = verify_reproduction(replay, parent)
    if _first_difference(
        config.as_dict(), replay.result.get("config"), "config"
    ):
        raise ReproductionMismatch(
            "group configuration differs from verified replay"
        )
    cohorts = {
        c.anchor_wave: c for c in (inputs.cohort, *inputs.additional_cohorts)
    }
    if any(c.data_provenance == g3.REGISTERED_REAL for c in cohorts.values()):
        if not isinstance(
            registration_pointer, str
        ) or not g3.REGISTRATION_POINTER.fullmatch(registration_pointer):
            raise ValueError(
                "real-data grouping requires a new issue #42 pointer"
            )
        if registration_pointer == parent.get("registration_pointer"):
            raise ValueError(
                "parent registration cannot authorize post hoc grouping"
            )
    loader = (
        g1.load_group_attributes
        if attribute_loader is None
        else attribute_loader
    )
    options = (
        LifetimeOptions() if lifetime_options is None else lifetime_options
    )
    scheme = g3.derive_scheme(
        g3.MINT8_SCHEME,
        scheme_id="projection_mint8_with_opening_lifetime",
        title="MINT8 annual rows with opening-cohort lifetime dimensions",
        append=_fixed_lifetime_dimensions(),
        notes=(
            "Lifetime quintiles use G3's weighted percentile rule within "
            "ten-year birth cohorts of the entire opening cohort, fixed "
            "across draws, scenarios and population variants.",
            INCOME_REASON,
        ),
    )
    attributes: dict[int, pd.DataFrame] = {}
    attribute_provenance = {}
    lifetime_provenance = {}
    for wave, cohort in cohorts.items():
        ids = tuple(int(pid) for pid in cohort.persons["person_id"])
        loaded = loader(ids, anchor_waves=(wave,))
        if loaded.frame["person_id"].duplicated().any() or set(
            loaded.frame["person_id"]
        ) != set(ids):
            raise ValueError(
                "G1 side frame must retain each opening person exactly once"
            )
        recorded = loaded.provenance.get("content_sha256")
        if recorded is not None and recorded != g1.content_sha256(
            loaded.frame
        ):
            raise ValueError("G1 side frame changed after sealing")
        side = loaded.frame[
            [
                "person_id",
                "race_ethnicity_mint8",
                "education_years",
                "country_of_birth_mint8",
            ]
        ].copy()
        side["race_ethnicity"] = _label_codes(
            side.pop("race_ethnicity_mint8"), g3.RACE_ETHNICITY_DIMENSION
        )
        side["country_of_birth"] = _label_codes(
            side.pop("country_of_birth_mint8"), g3.COUNTRY_OF_BIRTH_DIMENSION
        )
        lifetime, provenance = _lifetime_side(cohort, inputs.params, options)
        attributes[wave] = side.merge(
            lifetime, on="person_id", validate="one_to_one"
        )
        attribute_provenance[str(wave)] = loaded.provenance
        lifetime_provenance[str(wave)] = provenance
    if replay.exercise == "cola":
        row_config = {key: REGISTERED_ROWS[key] for key in config.rows}
    elif replay.exercise == "fra68":
        row_config = {key: config.row(key) for key in config.rows}
    else:
        raise ValueError("unknown projection exercise")
    output_rows = {}
    for row_id, benefits in replay.benefit_rows.items():
        row = row_config[row_id]
        wave = row.anchor_wave
        state = replay.states[wave][
            ["draw", "person_id", "sex", "marital_status"]
        ]
        frame = benefits.merge(
            state,
            on=["draw", "person_id"],
            how="left",
            validate="one_to_one",
            indicator=True,
        )
        if not frame["_merge"].eq("both").all():
            raise ValueError("beneficiary absent from final projected state")
        frame = frame.drop(columns="_merge").merge(
            attributes[wave],
            on="person_id",
            how="left",
            validate="many_to_one",
            indicator=True,
        )
        if not frame["_merge"].eq("both").all():
            raise ValueError("beneficiary absent from opening attribute frame")
        frame = frame.drop(columns="_merge")
        frame["age"] = config.reference_year - frame["birth_year"]
        frame["benefit_type"] = frame["benefit_components"].map(benefit_type)
        frame["poverty_status"] = None
        frame["household_income_quintile"] = float("nan")
        columns = {
            d.key: d.key for d in scheme.dimensions if d.kind != g3.TOTAL
        }
        columns["education"] = "education_years"
        cohort = cohorts[wave]
        if replay.exercise == "cola":
            tab_config = ColaAgeProfileConfig(
                reference_year=config.reference_year,
                components=row.components,
                benefit_period=row.tabulation_benefit_period,
                headline_statistic=row.headline_statistic,
                draw_indices=config.draw_indices,
                floor_seeds=config.floor_seeds,
            )
        else:
            from populace_dynamics.fra68_track.runner import _tabulation_config

            tab_config = _tabulation_config(row, config)
        frozen_row = replay.result["rows"][row_id]
        frozen_tabulation = frozen_row.get("tabulation") or {}
        labels = (
            tuple(
                frozen_row.get(
                    "labels", frozen_tabulation.get("labels", cohort.labels)
                )
            )
            + POST_HOC_LABELS
        )
        variants = {
            "test_population": frame,
            "mint_population": frame.loc[
                (frame["age"] >= 60)
                & frame["beneficiary_base"]
                & (frame["benefit_base"] > 0)
            ].copy(),
        }
        output_variants = {}
        for name, selected in variants.items():
            if set(selected["draw"]) != set(tab_config.draw_indices):
                output_variants[name] = {
                    "status": "not computed",
                    "reason": "population absent in at least one registered draw",
                    "labels": list(labels),
                }
                continue
            assignment = g3.assign_groups(
                selected,
                scheme,
                columns,
                key_columns=("draw", "person_id"),
                unclassified_codes={
                    "marital_status": (
                        "unknown",
                        "no_marriage_history",
                        "separated",
                    )
                },
            )
            result = g3.tabulate_projection_breakdown(
                selected,
                assignment,
                config=tab_config,
                data_provenance=cohort.data_provenance,
                registration_pointer=registration_pointer,
                labels=labels,
                post_hoc_labels=POST_HOC_LABELS,
                statistic_id=frozen_tabulation.get(
                    "statistic_id", g3.PROJECTION_STATISTIC_ID
                ),
                upstream={
                    "parent_sha256": parent_sha256,
                    "row": row_id,
                    "verified_payload_sha256": identity[
                        "verified_payload_sha256"
                    ],
                    "retention_sha256": replay.retention_sha256,
                    "reproduction_identical": True,
                    "absolute_tolerance": 0.0,
                    "relative_tolerance": 0.0,
                },
            ).as_dict()
            result["population_variant"] = name
            result["not_computed"] = {
                "poverty_status": INCOME_REASON,
                "household_income_quintile": INCOME_REASON,
                "household_income_statistics": INCOME_REASON,
                "official_poverty_statistics": INCOME_REASON,
            }
            output_variants[name] = result
        output_rows[row_id] = {
            "anchor_wave": wave,
            "row": frozen_row["row"],
            "labels": list(labels),
            "variants": output_variants,
        }
    invented = all(c.data_provenance == g3.INVENTED for c in cohorts.values())
    return {
        "header": (
            INVENTED_HEADER
            if invented
            else "Registered projection group breakdown"
        ),
        "exercise": replay.exercise,
        "labels": ([INVENTED_HEADER] if invented else [])
        + list(inputs.cohort.labels)
        + list(POST_HOC_LABELS),
        "report_only": True,
        "parent_sha256": parent_sha256,
        "reproduction": identity,
        "attribute_provenance": attribute_provenance,
        "lifetime_provenance": lifetime_provenance,
        "conventions": {
            "benefit_type": "baseline components; widow then spouse (dual entitlement included), otherwise worker only",
            "marital_status": "2030 projected state; opening divorced/never married carried forward; inherited opening convention counts separated as married; literal separated and unknown codes unclassified",
            "mint_population": "current-law beneficiaries aged 60 or older in 2030",
            "test_population": "alive in 2030 with a positive benefit in either scenario; original scenario membership retained",
            "artifact_choice": "one artifact per exercise, preserving separate parent identities and one-shot registrations",
            "lifetime": "opening-cohort careers only; no projected earnings or unsourced interest rates",
        },
        "rows": output_rows,
    }
