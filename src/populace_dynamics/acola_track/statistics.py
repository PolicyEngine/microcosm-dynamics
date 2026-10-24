"""Registration 18 statistics on invented or registered person-level rows.

The A7 normalizer, recipient masks, scenario means, draw summaries and
family-unit splitter are reused unchanged. Its public tabulator is bypassed
so it cannot publish an unregistered mean of individual ratios. The median
uses exact binary-float weights and the registered midpoint rule.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from fractions import Fraction
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.estimates import cola_age_profile as a7

P = "P"
P_OASI = "P_OASI"
P_DI = "P_DI"
RATIO_OF_SCENARIO_MEANS = a7.RATIO_OF_SCENARIO_MEANS
MEDIAN_INDIVIDUAL_PCT_CHANGE = "median_individual_pct_change"
DIFFERENCE_OF_WEIGHTED_MEDIANS_PCT = "difference_of_weighted_medians_pct"
BASELINE_FALLING_SHARE = "baseline_falling_share"
MEDIAN_BENEFIT_BASE = "median_benefit_base"
MEDIAN_BENEFIT_REFORM = "median_benefit_reform"
COST_STATISTICS = (P, P_OASI, P_DI, RATIO_OF_SCENARIO_MEANS)
MINT_STATISTICS = (
    RATIO_OF_SCENARIO_MEANS,
    MEDIAN_INDIVIDUAL_PCT_CHANGE,
    DIFFERENCE_OF_WEIGHTED_MEDIANS_PCT,
    BASELINE_FALLING_SHARE,
    MEDIAN_BENEFIT_BASE,
    MEDIAN_BENEFIT_REFORM,
)
MINT_BANDS = (
    ("Total", 62, None),
    ("62-69", 62, 69),
    ("70-79", 70, 79),
    ("80-89", 80, 89),
    ("90+", 90, None),
)
SPOUSE_WORKER_CLASSES = (
    "entitled_unconverted_di_worker",
    "another_worker",
    "unclassified",
)
OASI_COMPONENTS = tuple(
    c for c in a7.PRIMARY_COMPONENTS if c != "disabled_worker"
)
INTENDED_BOUND_VIOLATIONS = (
    {
        "mechanism": "L",
        "cause": "dual-entitlement spouse excess with different COLA clocks",
        "behavior": (
            "A claimant's own early retirement benefit and a later spouse "
            "excess have different age factors. The excess subtracts the "
            "full own PIA. Reducing that PIA can raise the combined benefit "
            "when the own clock carries more reduced increases than the "
            "linked worker's clock. Individual percent changes and P can "
            "exceed zero; larger cuts or earlier starts can raise them."
        ),
        "tolerance": (
            "This is a structural exception, not a rounding tolerance. "
            "No universal [N_full, 0] or monotonic cut bound is asserted."
        ),
        "source": (
            "scenario_benefits.spouse_excess_path; "
            "ss.benefits.spousal_benefit; cola_track_a.benefits._spouse_excess"
        ),
        "adjustment_applied": False,
    },
)


def weighted_median(
    values: Sequence[float],
    weights: Sequence[float],
    person_ids: Sequence[int | str] | None = None,
) -> float | None:
    """Exact-W/2 midpoint median, excluding zero-weight observations.

    Fraction(float(weight)) preserves the supplied binary float exactly.
    Equal values sort stably by person id. An empty positive-weight sample
    returns None; callers report the reason and zero-weight exclusions.
    """
    if len(values) != len(weights):
        raise a7.ColaTabulationError("values and weights differ in length")
    ids = list(range(len(values))) if person_ids is None else list(person_ids)
    if len(ids) != len(values):
        raise a7.ColaTabulationError("person_ids differ in length")
    if len({type(pid) for pid in ids}) > 1:
        raise a7.ColaTabulationError("person_ids must have one key type")
    atoms = []
    for value, weight, pid in zip(values, weights, ids, strict=True):
        value = a7._finite(float(value), "a median value")
        weight = a7._finite(float(weight), "a median weight")
        if weight < 0:
            raise a7.ColaTabulationError("median weights must be nonnegative")
        if weight > 0:
            atoms.append((value, pid, Fraction(weight)))
    if not atoms:
        return None
    atoms.sort(key=lambda atom: (atom[0], atom[1]))
    total = sum((atom[2] for atom in atoms), Fraction(0))
    cumulative = Fraction(0)
    for index, (value, _, weight) in enumerate(atoms):
        cumulative += weight
        if 2 * cumulative == total:
            # All remaining weights are positive, so a next atom exists.
            return a7._finite(
                float((Fraction(value) + Fraction(atoms[index + 1][0])) / 2),
                "the midpoint weighted median",
            )
        if 2 * cumulative > total:
            return value
    raise AssertionError("positive weights must cross the median")


def _empty_rows() -> a7._Rows:
    """An emitted row can have no beneficiaries in any configured draw."""
    ints = np.array([], dtype=np.int64)
    floats = np.array([], dtype=np.float64)
    booleans = np.array([], dtype=bool)
    return a7._Rows(
        draw=ints,
        person_id=np.array([], dtype=object),
        family_unit_id=np.array([], dtype=object),
        weight=floats,
        birth_year=ints,
        age=ints,
        group=ints,
        selected_base=floats,
        selected_reform=floats,
        recipient_base=booleans,
        recipient_reform=booleans,
        flagged_zero_base=0,
        flagged_zero_reform=0,
        n_persons_weight_varies=0,
        extra_columns=(),
    )


def _prepare(
    records,
    draw_indices,
    floor_seeds,
    reference_year,
    age_rule,
    certified_draw_indices=None,
):
    config = a7.ColaAgeProfileConfig(
        reference_year=reference_year,
        age_rule=age_rule,
        age_groups=(a7.AgeGroup("all", 0, None),),
        draw_indices=tuple(draw_indices),
        floor_seeds=tuple(floor_seeds),
        allow_membership_difference=True,
        membership_basis=a7.SCENARIO_SPECIFIC,
    )
    records, _ = a7._records(records)
    normalize_config = config
    if certified_draw_indices is not None:
        certified = tuple(sorted(certified_draw_indices))
        if certified != config.draw_indices:
            raise a7.ColaTabulationError(
                "certified projection draw inventory differs from configured draws"
            )
        present = tuple(
            sorted({a7._int_value(r["draw"], "draw") for r in records})
        )
        if not set(present) <= set(certified):
            raise a7.ColaTabulationError("rows contain an uncertified draw")
        if present:
            normalize_config = replace(config, draw_indices=present)
    rows = (
        a7._normalize(records, normalize_config) if records else _empty_rows()
    )
    if np.any(rows.group < 0):
        raise a7.ColaTabulationError("a person lies outside the all-ages cell")
    # A7 validates ids before they are sorted. Every output and summation
    # thereafter sees the same draw/person order, independent of input order.
    order = sorted(
        range(rows.n), key=lambda i: (int(rows.draw[i]), rows.person_id[i])
    )
    records = [records[i] for i in order]
    arrays = {
        name: getattr(rows, name)[order]
        for name in (
            "draw",
            "person_id",
            "family_unit_id",
            "weight",
            "birth_year",
            "age",
            "group",
            "selected_base",
            "selected_reform",
            "recipient_base",
            "recipient_reform",
        )
    }
    return records, replace(rows, **arrays), config


def _scenario_cell(rows, selected, draw):
    cell = a7._cell(
        rows,
        selected,
        a7._membership_masks(rows, a7.SCENARIO_SPECIFIC),
        draw,
    )
    # A7 computes this internally; it is not registered for A-COLA.
    cell.pop(a7.MEAN_OF_INDIVIDUAL_RATIOS)
    cell["undefined_reasons"].pop(a7.MEAN_OF_INDIVIDUAL_RATIOS, None)
    intermediate = {"undefined_reasons": {}}
    for scenario in ("base", "reform"):
        key = f"mean_benefit_{scenario}"
        intermediate[key] = cell.pop(key)
        if intermediate[key] is None:
            intermediate["undefined_reasons"][
                key
            ] = f"empty_{scenario}_membership"
    cell["not_registered"] = intermediate
    return cell


def _percent(total_base, total_reform, key, reasons):
    if total_base <= 0:
        reasons[key] = "nonpositive_baseline_total"
        return None
    # Match v2's arithmetic order, rather than subtracting totals first.
    return a7._finite(100 * (total_reform / total_base - 1), key)


def _component_matrix(records):
    amounts = np.zeros((len(records), len(a7.PRIMARY_COMPONENTS), 2))
    for i, record in enumerate(records):
        parsed = a7._parse_components(record["benefit_components"], i)
        for j, component in enumerate(a7.PRIMARY_COMPONENTS):
            if component in parsed:
                amounts[i, j] = parsed[component]
    return amounts


def _cost_cell(rows, components, spouse_classes, selected, draw):
    cell = _scenario_cell(rows, selected, draw)
    totals = {
        c: {
            scenario: a7._fsum(
                rows.weight[selected] * components[selected, j, s]
            )
            for s, scenario in enumerate(("base", "reform"))
        }
        for j, c in enumerate(a7.PRIMARY_COMPONENTS)
    }
    total_base = a7._fsum(rows.weight[selected] * rows.selected_base[selected])
    total_reform = a7._fsum(
        rows.weight[selected] * rows.selected_reform[selected]
    )
    reasons = cell["undefined_reasons"]
    cell[P] = _percent(total_base, total_reform, P, reasons)
    group_shares = {}
    for label, chosen, key in (
        ("OASI", OASI_COMPONENTS, P_OASI),
        ("DI", ("disabled_worker",), P_DI),
    ):
        base = math.fsum(totals[c]["base"] for c in chosen)
        reform = math.fsum(totals[c]["reform"] for c in chosen)
        cell[key] = _percent(base, reform, key, reasons)
        group_shares[label] = base / total_base if total_base > 0 else None
        if total_base <= 0:
            reasons[f"group_share_{label}"] = "nonpositive_baseline_total"
    spouse = components[:, a7.PRIMARY_COMPONENTS.index("spouse"), :]
    spouse_memo = {}
    for label in SPOUSE_WORKER_CLASSES:
        memo = {}
        for s, scenario in enumerate(("base", "reform")):
            mask = selected & (spouse_classes == label) & (spouse[:, s] > 0)
            memo[f"n_{scenario}"] = int(np.count_nonzero(mask))
            memo[f"weighted_count_{scenario}"] = a7._fsum(rows.weight[mask])
            memo[f"dollars_{scenario}"] = a7._fsum(
                rows.weight[mask] * spouse[mask, s]
            )
        spouse_memo[label] = memo
    cell.update(
        T_base=total_base,
        T_reform=total_reform,
        component_totals=totals,
        group_shares=group_shares,
        spouse_worker_classes=spouse_memo,
    )
    return cell


def _mint_cell(rows, selected, draw):
    cell = _scenario_cell(rows, selected, draw)
    base, reform, alt = (
        selected & mask
        for mask in a7._membership_masks(rows, a7.SCENARIO_SPECIFIC)
    )
    reasons = cell["undefined_reasons"]
    for key, mask, values, reason in (
        (
            MEDIAN_BENEFIT_BASE,
            base,
            rows.selected_base,
            "empty_positive_weight_baseline_membership",
        ),
        (
            MEDIAN_BENEFIT_REFORM,
            reform,
            rows.selected_reform,
            "empty_positive_weight_reform_membership",
        ),
    ):
        cell[key] = weighted_median(
            values[mask], rows.weight[mask], rows.person_id[mask]
        )
        if cell[key] is None:
            reasons[key] = reason
    changes = 100 * (rows.selected_reform[alt] / rows.selected_base[alt] - 1)
    cell[MEDIAN_INDIVIDUAL_PCT_CHANGE] = weighted_median(
        changes, rows.weight[alt], rows.person_id[alt]
    )
    if cell[MEDIAN_INDIVIDUAL_PCT_CHANGE] is None:
        reasons[MEDIAN_INDIVIDUAL_PCT_CHANGE] = (
            "empty_positive_weight_alternative_membership"
        )
    mb, mr = cell[MEDIAN_BENEFIT_BASE], cell[MEDIAN_BENEFIT_REFORM]
    if mb is None or mr is None:
        cell[DIFFERENCE_OF_WEIGHTED_MEDIANS_PCT] = None
        reasons[DIFFERENCE_OF_WEIGHTED_MEDIANS_PCT] = (
            "baseline_or_reform_median_undefined"
        )
    else:
        cell[DIFFERENCE_OF_WEIGHTED_MEDIANS_PCT] = _percent(
            mb, mr, DIFFERENCE_OF_WEIGHTED_MEDIANS_PCT, reasons
        )
    falls = base & (rows.selected_reform < rows.selected_base)
    falling_weight = a7._fsum(rows.weight[falls])
    if cell["weight_base"] > 0:
        cell[BASELINE_FALLING_SHARE] = falling_weight / cell["weight_base"]
    else:
        cell[BASELINE_FALLING_SHARE] = None
        reasons[BASELINE_FALLING_SHARE] = "empty_baseline_membership"
    cell["n_baseline_falling"] = int(np.count_nonzero(falls))
    cell["weight_baseline_falling"] = falling_weight
    cell["median_zero_weight_exclusions"] = {
        key: int(np.count_nonzero(mask & (rows.weight == 0)))
        for key, mask in (("base", base), ("reform", reform), ("alt", alt))
    }
    return cell


def _summary(cells, statistic):
    summary = a7._draw_summary(cells, statistic)
    summary["sd"] = summary["sample_sd"]
    summary["undefined_reason"] = (
        None if summary["defined"] else "one_or_more_undefined_draws"
    )
    summary["undefined_reasons"] = {}
    if summary["sample_sd"] is None:
        summary["undefined_reasons"]["sample_sd"] = (
            summary["undefined_reason"] or "fewer_than_two_draws"
        )
        summary["undefined_reasons"]["sd"] = summary["undefined_reasons"][
            "sample_sd"
        ]
    return summary


def _refused_cell(template, reason):
    """Keep the complete memo shape without calling unknown amounts zero."""
    reasons = {}

    def unknown(value, path):
        if isinstance(value, dict):
            return {
                key: unknown(nested, f"{path}.{key}" if path else key)
                for key, nested in value.items()
            }
        if isinstance(value, int | float) or value is None:
            reasons[path] = reason
            return None
        return value

    cell = {
        key: unknown(value, key)
        for key, value in template.items()
        if key not in ("draw", "undefined_reasons")
    }
    cell["draw"] = template["draw"]
    cell["undefined_reasons"] = reasons
    intermediate = cell.get("not_registered")
    if intermediate is not None:
        intermediate["undefined_reasons"] = {
            key: reason
            for key, value in intermediate.items()
            if key != "undefined_reasons" and value is None
        }
    cell["status"] = "refused"
    cell["refusal_reason"] = reason
    return cell


def _summarize(rows, config, bands, statistics, cell_fn, refused_draws=None):
    refused = dict(refused_draws or {})
    if not set(refused) <= set(config.draw_indices):
        raise a7.ColaTabulationError(
            "refused_draws contain an unconfigured draw"
        )
    if any(
        not isinstance(reason, str) or not reason
        for reason in refused.values()
    ):
        raise a7.ColaTabulationError(
            "every refused draw needs a nonempty reason"
        )
    subsets = {
        label: (rows.age >= lower)
        & (np.ones(rows.n, dtype=bool) if upper is None else rows.age <= upper)
        for label, lower, upper in bands
    }

    def evaluate(selected, draw):
        if draw in refused:
            empty_cell = cell_fn(np.zeros(rows.n, dtype=bool), draw)
            return _refused_cell(empty_cell, refused[draw])
        return cell_fn(selected, draw)

    def profile(subset):
        return {
            label: [
                evaluate(subset & mask & (rows.draw == draw), draw)
                for draw in config.draw_indices
            ]
            for label, mask in subsets.items()
        }

    full = profile(np.ones(rows.n, dtype=bool))
    output = {
        label: {
            "per_draw": cells,
            "statistics": {key: _summary(cells, key) for key in statistics},
            "floor_per_seed": [],
        }
        for label, cells in full.items()
    }
    unit_frame = pd.DataFrame({a7.FAMILY_UNIT: rows.family_unit_id.tolist()})
    for seed in config.floor_seeds:
        in_a = np.zeros(rows.n, dtype=bool)
        if rows.n:
            side, _ = a7.split_panel_by_person(
                unit_frame, a7.FAMILY_UNIT, fraction=0.5, seed=seed
            )
            in_a[side.index.to_numpy()] = True
        side_a, side_b = profile(in_a), profile(~in_a)
        for label in output:
            a = {key: _summary(side_a[label], key) for key in statistics}
            b = {key: _summary(side_b[label], key) for key in statistics}
            gaps, reasons = {}, {}
            for key in statistics:
                ma, mb = a[key]["mean"], b[key]["mean"]
                gaps[key] = None if ma is None or mb is None else abs(ma - mb)
                if gaps[key] is None:
                    reasons[key] = "one_or_both_half_sample_means_undefined"
            output[label]["floor_per_seed"].append(
                {
                    "seed": seed,
                    "side_a": a,
                    "side_b": b,
                    "absolute_gaps": gaps,
                    "undefined_reasons": reasons,
                }
            )
    for band in output.values():
        for key in statistics:
            usable, dropped = [], []
            for seed in band["floor_per_seed"]:
                gap = seed["absolute_gaps"][key]
                if gap is None:
                    dropped.append(seed["seed"])
                else:
                    usable.append(gap)
            band["statistics"][key]["floor"] = {
                **a7._floor_summary(usable),
                "dropped_seeds": dropped,
            }
    return output


def _input_summary(rows):
    return {
        "n_rows": rows.n,
        "n_persons": len(set(rows.person_id)),
        "n_family_units": len(set(rows.family_unit_id)),
        "n_persons_weight_varies_across_draws": rows.n_persons_weight_varies,
        "extra_columns_ignored_by_a7": list(rows.extra_columns),
        "zero_weight_rows": int(np.count_nonzero(rows.weight == 0)),
        "membership_basis": a7.SCENARIO_SPECIFIC,
        "recipient_rule": a7.POSITIVE_BENEFIT,
        "median_weight_arithmetic": "exact Fraction of supplied float",
        "median_tie_sort": "value ascending, then person_id ascending",
        "median_zero_weight_rule": "exclude and report counts",
        "floor_split_population": "entire normalized row table",
        "floor_split_rule": "Bernoulli(0.5), sorted opening family ids",
    }


def summarize_cost(
    records: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    draw_indices: Sequence[int],
    floor_seeds: Sequence[int] = a7.DEFAULT_FLOOR_SEEDS,
    certified_draw_indices: Sequence[int] | None = None,
    refused_draws: Mapping[int, str] | None = None,
) -> dict[str, Any]:
    """All-ages totals, split, spouse memo, draw summaries and A7 floors."""
    records, rows, config = _prepare(
        records,
        draw_indices,
        floor_seeds,
        2030,
        "reference_year_minus_birth_year",
        certified_draw_indices,
    )
    components = _component_matrix(records)
    spouse_classes = np.array(
        [r.get("spouse_worker_class", "unclassified") for r in records],
        dtype=object,
    )
    if any(c not in SPOUSE_WORKER_CLASSES for c in spouse_classes):
        raise a7.ColaTabulationError("unknown spouse_worker_class")
    output = _summarize(
        rows,
        config,
        (("all", 0, None),),
        COST_STATISTICS,
        lambda selected, draw: _cost_cell(
            rows, components, spouse_classes, selected, draw
        ),
        refused_draws,
    )["all"]
    output["input_summary"] = _input_summary(rows)
    output["certified_projection_draws"] = (
        list(config.draw_indices)
        if certified_draw_indices is not None
        else None
    )
    output["statistic_additions"] = [P_OASI, P_DI, RATIO_OF_SCENARIO_MEANS]
    output["intended_bound_violations"] = [
        dict(item) for item in INTENDED_BOUND_VIOLATIONS
    ]
    return output


def summarize_mint(
    records: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    draw_indices: Sequence[int],
    floor_seeds: Sequence[int] = a7.DEFAULT_FLOOR_SEEDS,
    reference_year: int = 2030,
    age_rule: str = "reference_year_minus_birth_year",
    certified_draw_indices: Sequence[int] | None = None,
    refused_draws: Mapping[int, str] | None = None,
) -> dict[str, Any]:
    """All five MINT bands; memo statistics receive draw SDs and floors."""
    _, rows, config = _prepare(
        records,
        draw_indices,
        floor_seeds,
        reference_year,
        age_rule,
        certified_draw_indices,
    )
    return {
        "bands": _summarize(
            rows,
            config,
            MINT_BANDS,
            MINT_STATISTICS,
            lambda selected, draw: _mint_cell(rows, selected, draw),
            refused_draws,
        ),
        "input_summary": _input_summary(rows),
        "certified_projection_draws": (
            list(config.draw_indices)
            if certified_draw_indices is not None
            else None
        ),
        "falling_share_units": "fraction of baseline beneficiary weight",
        "benefit_level_units": "annual, 12 times the row monthly amount",
        "intended_bound_violations": [
            dict(item) for item in INTENDED_BOUND_VIOLATIONS
        ],
    }
