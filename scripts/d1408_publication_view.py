"""Reduce d1408 aggregates to the public schema and prove it differences safely.

Verification class: labelled diagnostic publication guard under ruling
d1408. It reads only already-suppressed aggregate dictionaries, never
microdata. The first review round showed that publishing many nested
subtotals let a reader recover groups of fewer than ten people by
subtraction. The public view therefore keeps, per result and wave, one
flagged subtotal and the admitted denominators; it reports each payment
path only as "none", "fewer than ten", "ten or more" or "withheld". Every
published positive count declares, in a ``population`` field, the id of the
population it measures. ``differencing_violations`` pools counts by that
id, asserts that every cell sharing an id has the same count and weight,
and sweeps every signed combination of the distinct populations within a
family, with no size limit, refusing any that equals one through nine.
"""

from __future__ import annotations

import math

SMALL = "<10"
NONE = "none"
FEWER_THAN_TEN = "fewer than ten"
TEN_OR_MORE = "ten or more"
WITHHELD = "withheld"

# Results that describe the same people are differenced together.
FAMILIES = {
    "first_estimates": "first_estimates",
    "track_m_minimum_benefit": "track_m",
    "r7_sharing": "r7",
    "cost_ordering_r7": "r7",
    "cola": "projection",
    "fra68": "projection",
}
PEOPLE_KEYS = frozenset(
    {
        "people",
        "admitted_people",
        "changed_recipients",
        "changed_receiving_people",
        "people_upper_bound",
        "real_roster_people",
        "pre1917_flagged_people",
        "pre1917_evaluations",
        "pre1917_flagged_evaluations",
    }
)
RECORD_KEYS = frozenset({"worker_records", "admitted_worker_records"})
MAX_CELLS = 20


def path_category(cell) -> str:
    """Describe a payment-path cell without publishing its count."""
    if cell is None:
        return NONE
    people = cell.get("people") if isinstance(cell, dict) else cell
    if isinstance(people, bool):
        raise ValueError("boolean is not a people count")
    if isinstance(people, int):
        if people < 0:
            raise ValueError("negative people count")
        return (
            NONE
            if people == 0
            else (FEWER_THAN_TEN if people < 10 else TEN_OR_MORE)
        )
    if people == SMALL:
        return FEWER_THAN_TEN
    if isinstance(people, str):
        return WITHHELD
    raise ValueError(f"unrecognized path cell: {cell!r}")


def flagged_cell(
    cell, population: str, *, records: bool = True, share_key=None
) -> dict:
    """Keep a flagged subtotal's count, records, weight and share only.

    ``records=False`` drops the worker-record count where people and
    records are not one-to-one, so their difference would carry
    information about a withheld path. ``share_key`` renames the share to
    name its denominator.
    """
    keys = ("people", "worker_records", "weight", "admitted_weight_share")
    out = {key: cell[key] for key in keys if key in cell}
    if not records:
        out.pop("worker_records", None)
    elif (
        isinstance(out.get("people"), int)
        and out.get("worker_records") == out["people"]
    ):
        # One flagged worker record per person: publish that fact, not a
        # second count of the same group in another unit.
        out.pop("worker_records")
        out["one_worker_record_per_person"] = True
    if share_key is not None and "admitted_weight_share" in out:
        out[share_key] = out.pop("admitted_weight_share")
    out["population"] = population
    return out


def _copy(result, keys):
    return {key: result[key] for key in keys if key in result}


IDENTITY = (
    "header",
    "label",
    "result",
    "artifact",
    "code_commit",
    "code_commit_basis",
    "commit_basis",
    "code_commit_reason",
    "parameter_commit",
    "verification",
    "method",
    "real_data_files_read",
    "guard_findings",
    "pre_1917_refusal",
    "historical_source_identity",
)


def first_estimates_view(result) -> dict:
    counts = result["counts"]
    view = _copy(
        result,
        IDENTITY
        + (
            "reproduction_check",
            "headline_changes",
            "headline_changes_reason",
            "parameter_bundle_verified",
            "registration_configurations",
        ),
    )
    view["counts"] = {
        "real_roster": {
            "people": counts["real_roster_people"],
            "weight": counts["real_roster_weight"],
            "population": "first_estimates/report_seed_roster",
        },
        "support_upper_bound": dict(
            counts["support_upper_bound"],
            population="first_estimates/supported_birth_cohort",
        ),
        "actual_person_upper_bound": dict(
            counts["actual_person_upper_bound"],
            population="first_estimates/actual_person_upper_bound",
        ),
        "expected_support_bound": dict(
            counts["expected_support_bound"],
            population="first_estimates/expected_support_bound",
        ),
        # The per-draw bound is the same 21-person set divided by each
        # draw's committed denominator, so only its share is repeated.
        "upper_bound_shares_by_draw": [
            {
                "draw_index": row["draw_index"],
                "admitted_weight_share_upper_bound": row[
                    "admitted_weight_share_upper_bound"
                ],
            }
            for row in counts[
                "upper_bounds_with_committed_admitted_denominators"
            ]
        ],
        # Each share is the bound's weight divided by that draw's admitted
        # weight in the committed artifact; the counts are not republished.
        "share_denominators": (
            "runs/first_estimates_v1.json, each draw's admitted weight"
        ),
        "pre1917_evaluations": counts["pre1917_evaluations"],
        "pre1917_reason": counts["pre1917_reason"],
    }
    return view


def _zero_change_summary(rows) -> dict:
    """Summarize Track M's row changes; refuse anything but exact zeros."""
    cells = 0
    for row in rows.values():
        for change in row["changes"].values():
            cells += 1
            if (
                change["changed_receiving_people"] != 0
                or change["supported_subset_change_percentage_points"] != 0
                or change["change_in_admitted_people"] != 0
            ):
                raise ValueError(
                    "a nonzero Track M change needs a reviewed public form"
                )
    exact = all(
        cell["exact_match"]
        for row in rows.values()
        for cell in row["legacy_reproduction"].values()
    )
    return {
        "cells": cells,
        "legacy_reproduction_exact_in_every_cell": exact,
        "changed_receiving_people_in_every_cell": 0,
        "model_share_change_percentage_points_in_every_cell": 0.0,
    }


def minimum_view(result) -> dict:
    view = _copy(
        result,
        IDENTITY
        + ("psid_files_match_artifact_sha256", "legacy_reproduction_verified"),
    )
    readings = {}
    for name, reading in result["readings"].items():
        supported = reading["supported"]
        public = {
            "flagged_supported": (
                # Track M's people include linked beneficiaries of flagged
                # owners, so people minus worker records would bound the
                # withheld linked-auxiliary cell; only people are published.
                flagged_cell(
                    supported["all_flagged_evaluations"],
                    "track_m/scored/flagged_supported",
                    records=False,
                )
                if name == "scored"
                else WITHHELD
            ),
            "paths": {
                key: path_category(supported[key])
                for key in (
                    "admitted_flagged_worker_owners",
                    "linked_auxiliary_basis",
                    "factor_entered_survivor_payment_gate",
                    "factor_entered_inverse_ms5_pia",
                )
            },
            "pre1917_flagged_people": reading["pre1917_unsupported"][
                "all_flagged_evaluations"
            ]["people"],
            "changes": _zero_change_summary(reading["rows"]),
            "legacy_reproduction_verified": reading[
                "legacy_reproduction_verified"
            ],
        }
        if name == "scored":
            # Only the scored reading's denominators are public: the
            # sensitivity reading's record total differs from it by a
            # small removed-record group.
            public["admitted"] = {
                "people": reading["admitted_people"],
                "worker_records": reading["admitted_worker_records"],
                "weight": reading["admitted_weight"],
                "population": "track_m/scored/admitted",
            }
        readings[name] = public
    view["readings"] = readings
    return view


def _share_cells(model_shares) -> dict:
    out = {}
    for package, cells in model_shares.items():
        out[package] = {}
        for cell, value in cells.items():
            if value["affected_people"] == 0:
                changes = [
                    leaf
                    for group in (
                        "model_bucket_changes_pp",
                        "model_threshold_changes_pp",
                    )
                    for leaf in value.get(group, {}).values()
                ]
                if any(change != 0 for change in changes):
                    raise ValueError("unaffected cell reports a change")
                out[package][cell] = "no change"
            else:
                out[package][cell] = WITHHELD
    return out


def sharing_view(result) -> dict:
    view = _copy(result, IDENTITY + ("reproduction",))
    # Cost ordering's R7 component scores R7's own StudyData frame
    # (scripts/replication_cost_ordering.py builds R7's StudyData and calls
    # R7's score_population), so both results measure one population.
    view["admitted"] = dict(result["admitted"], population="r7_frame/admitted")
    view["flagged_supported"] = flagged_cell(
        result["flagged_supported"]["admitted_recipients"],
        "r7_frame/flagged_supported",
    )
    view["pre1917_flagged_people"] = result["flagged_pre_1917"][
        "admitted_recipients"
    ]["people"]
    flow = result["flow"]
    view["paths"] = {
        key: path_category(flow[key]["admitted_recipients"])
        for key in (
            "entered_changed_computed_payment",
            "computed_own_payment",
            "linked_survivor_basis",
        )
    }
    view["paths"]["inverse_ms5_pia"] = flow["inverse_ms5_pia"]
    view["paths"]["disability_basis"] = flow["disability_basis"]
    changes = result["changes"]
    view["changes"] = {
        "status": changes["status"],
        "aggregate_cost_change_pp": changes["aggregate_cost_change_pp"],
        "model_share_cells": _share_cells(changes["model_shares"]),
    }
    return view


PROJECTION_PATHS = (
    "own_record",
    "linked_spouse_basis",
    "deceased_auxiliary_basis",
    "opening_stock_adjustment",
    "positive_worker_payment",
    "positive_survivor_payment",
    "positive_spouse_basis_factor_unused",
    "positive_opening_stock_adjustment",
)


def projection_pre1917(result) -> int | str:
    """Zero only when no wave or row emits a positive pre-1917 cell."""
    cells = [
        value
        for wave in result.get("counts", {}).values()
        for key, value in wave.items()
        if key.startswith("unsupported_pre1917/")
    ] + [
        value
        for row in result.get(
            "admitted_beneficiary_counts_by_row", {}
        ).values()
        for key, value in row.items()
        if key.startswith("unsupported_pre1917/")
    ]
    if all(
        isinstance(cell, dict) and cell.get("people") == 0 for cell in cells
    ):
        return 0
    return WITHHELD


def projection_view(result) -> dict:
    view = _copy(
        result,
        IDENTITY
        + (
            "reproduction_check",
            "changed_recipient_definition",
            "counts_verified",
            "cross_result_publication_audit",
            "headline_changes",
        ),
    )
    view["pre1917_flagged_evaluations"] = projection_pre1917(result)
    waves = {}
    for wave, counts in result["counts"].items():
        flagged = counts.get("supported/factor_evaluation")
        waves[wave] = {
            "seed_cohort_weight": counts["seed_cohort_weight"],
            "flagged_supported": (
                flagged_cell(
                    flagged,
                    f"{result['result']}/{wave}/flagged_supported",
                    share_key="seed_cohort_weight_share",
                )
                if flagged is not None
                else {"people": 0, "worker_records": 0, "weight": 0}
            ),
            "paths": {
                role: path_category(counts.get(f"supported/{role}"))
                for role in PROJECTION_PATHS
            },
        }
    view["waves"] = waves
    # Row denominators are not published: rows that differ in benefit
    # period, components or wave cannot be shown to share a population,
    # and the flagged shares use each wave's seed-cohort weight.
    view["headline_changes"] = _declare_changed(
        result["result"], result.get("headline_changes", {})
    )
    return view


def _declare_changed(name, changes) -> dict:
    """Give each row's and group's changed-recipient count its population."""
    out = {}
    for row, value in changes.items():
        row_out = dict(value)
        row_out["population"] = f"{name}/{row}/changed_recipients"
        row_out["groups"] = {
            group: dict(
                cell,
                population=f"{name}/{row}/{group}/changed_recipients",
            )
            for group, cell in value.get("groups", {}).items()
        }
        out[row] = row_out
    return out


VIEWS = {
    "first_estimates": first_estimates_view,
    "track_m_minimum_benefit": minimum_view,
    "r7_sharing": sharing_view,
    "cost_ordering_r7": sharing_view,
    "cola": projection_view,
    "fra68": projection_view,
}


def public_view(result) -> dict:
    """Return the reviewed public schema for one diagnostic result."""
    return VIEWS[result["result"]](result)


WEIGHT_KEYS = ("weight", "admitted_weight", "weight_upper_bound")


def published_counts(document):
    """Yield (family, unit, path, value) for every published integer count."""
    for family, unit, path, value, *_ in published_cells(document):
        yield family, unit, path, value


def published_cells(document):
    """Yield (family, unit, path, value, weight, population) per count.

    ``weight`` is the summed weight published beside the count in the same
    cell, or None; ``population`` is the cell's declared population id.
    """
    for index, result in enumerate(document["results"]):
        family = FAMILIES[result["result"]]
        yield from _walk(result, family, (f"results[{index}]",))


def _walk(value, family, path):
    if isinstance(value, dict):
        weight = next(
            (
                value[key]
                for key in WEIGHT_KEYS
                if isinstance(value.get(key), (int, float))
                and not isinstance(value.get(key), bool)
            ),
            None,
        )
        for key, item in value.items():
            here = path + (key,)
            if (key in PEOPLE_KEYS or key in RECORD_KEYS) and _is_count(item):
                unit = "people" if key in PEOPLE_KEYS else "worker_records"
                yield (
                    family,
                    unit,
                    "/".join(here),
                    item,
                    weight,
                    value.get("population"),
                )
            else:
                yield from _walk(item, family, here)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, family, path + (str(index),))


def _is_count(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and float(value).is_integer()
    )


def distinct_cells(document):
    """Pool positive counts by family, one entry per population and unit.

    People and worker-record counts share a pool: a difference between a
    group's people and its records can carry information (each owner has
    one own record), so the sweep combines them too.

    Every positive count must declare the population it measures. A
    population republished in several cells (the R7 frame in R7 and cost
    ordering, for example) enters the sweep once, and every cell that
    shares its id must publish the same count and weight. Different ids
    never merge, whatever their values. Raises if a pool exceeds
    ``MAX_CELLS`` distinct populations, the bound that keeps the full sweep
    and its brute-force check cheap.
    """
    pools = {}
    for family, unit, path, value, weight, population in published_cells(
        document
    ):
        if value <= 0:
            continue
        if not isinstance(population, str) or not population:
            raise ValueError(f"published count without a population: {path}")
        cells = pools.setdefault(family, {})
        cell = cells.setdefault(
            (population, unit),
            {
                "population": population,
                "unit": unit,
                "value": int(value),
                "weight": weight,
                "paths": [],
            },
        )
        if cell["value"] != int(value) or cell["weight"] != weight:
            raise ValueError(
                f"population {population} ({unit}) does not match across "
                "cells: "
                f"{cell['paths'][0]} has {cell['value']} (weight "
                f"{cell['weight']}), {path} has {int(value)} (weight {weight})"
            )
        cell["paths"].append(path)
    out = {}
    for pool, cells in sorted(pools.items()):
        if len(cells) > MAX_CELLS:
            raise ValueError(
                f"{pool} publishes {len(cells)} distinct populations, more "
                f"than the {MAX_CELLS} the full differencing sweep is "
                "bounded to"
            )
        out[pool] = list(cells.values())
    return out


def reachable_sums(values):
    """Every sum of a subset of ``values`` with signs +1 or -1, exactly.

    Returns {sum: witness}, where the witness lists (index, sign) pairs.
    This is the full sweep over all 3**n signed subsets, computed by
    dynamic programming over the sums rather than by listing subsets.
    """
    reached = {0: ()}
    for index, value in enumerate(values):
        step = {}
        for total, witness in reached.items():
            for sign in (1, -1):
                candidate = total + sign * value
                if candidate not in reached and candidate not in step:
                    step[candidate] = witness + ((index, sign),)
        reached.update(step)
    return reached


def differencing_violations(document):
    """Every signed combination of distinct published counts, pooled by
    population family (people and worker records together), that equals
    one through nine.

    No subset size limit: all 3**n sign patterns over the pool's distinct
    populations are covered. This over-approximates real set differencing
    (unrelated populations are combined too), which errs on the safe side.
    A single published count of one through nine is a violation too.
    """
    violations = []
    for family, cells in distinct_cells(document).items():
        reached = reachable_sums([cell["value"] for cell in cells])
        for total in range(1, 10):
            if total in reached:
                violations.append(
                    {
                        "family": family,
                        "value": total,
                        "terms": [
                            ("+" if sign > 0 else "-")
                            + f"{cells[i]['unit']}:{cells[i]['paths'][0]}"
                            for i, sign in reached[total]
                        ],
                    }
                )
    return violations
