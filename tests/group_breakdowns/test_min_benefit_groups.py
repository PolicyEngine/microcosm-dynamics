"""Exercise 4 (Track M) by MINT8 subgroups, on INVENTED data (NASI G4c).

INVENTED DATA - NOT A COMPARISON.  Unit tier: the cohort is
``min_benefit_track_m.invented_psid``'s PSID-shaped frames, the
parameters ``min_benefit_track_m.invented.invented_parameters`` (no
policyengine-us checkout is read) and the side frame
``group_breakdowns.common.invented_group_attribute_inputs`` through G1's
real builder.  The "committed parent" is the registered computation run
once on those frames, through the registered runner's JSON encoding.

Invariants stated and tested here:

1. **Order.**  Nothing about groups is computed unless the re-executed
   registered computation equals the parent exactly: a parent with any one
   committed cell moved (a share, a design SE, a floor, a cohort-structure
   count, a d430 cell, the parameters, the PSID file hashes) is refused,
   and the side-frame loader is never called.
2. **Partition.**  In every breakdown and every dimension, the categories
   and the unclassified rows partition Total: unweighted counts exactly,
   weighted counts and weighted numerators to float summation.
3. **Differential.**  Every group cell's share equals the direct formula
   ``100 * fsum(w A) / fsum(w)`` over the group's rows (bit for bit), and
   G3's Total, Female and Male cells equal Track M's All, Women and Men
   cells exactly (the run's own consistency checks, recomputed here).
4. **Bounds.**  Shares lie in [0, 100]; standard errors and floors are
   nonnegative; every age is at least 62.
5. **Benefit type** (:func:`min_benefit.benefit_type_2022`): property-
   tested over every combination of the six type items, receipt and
   record basis.
"""

from __future__ import annotations

import copy
import dataclasses
import itertools
import json
import math
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import social_security_receipt as ssr
from populace_dynamics.estimates import group_breakdown as g3
from populace_dynamics.estimates import lifetime_measures as g2
from populace_dynamics.group_breakdowns import common
from populace_dynamics.group_breakdowns import min_benefit as mb
from populace_dynamics.min_benefit_track_m import (
    OUTPUT_LABELS,
    cohort,
    invented,
    invented_psid,
    tabulation,
)
from populace_dynamics.min_benefit_track_m.evaluation import (
    INVENTED,
    PSID_FILES,
)
from populace_dynamics.min_benefit_track_m.policy import (
    REGISTERED_ROWS,
    TABLE6_OPTIONS,
)

SEED = 11
FAMILY_UNITS = 40
SIDE_FRAME_SEED = 3
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-7"
)
_BENEFIT_CODES = {
    "retired_worker_only",
    "widower",
    "spousal",
    "disabled_worker_only",
}


def _frames():
    # Receipt of unknown or "other" type before 62 for a third of persons,
    # so d430's sensitivity reading differs from the scored one.
    return invented_psid.invented_cohort_inputs(
        seed=SEED,
        n_family_units=FAMILY_UNITS,
        unknown_or_other_before_62=0.3,
    )


def _reexecute(frames, params, cola):
    return mb.reexecute_track_m(
        frames,
        params,
        cola_rates=cola,
        data_provenance=INVENTED,
        registration_pointer=None,
        provenance_kind=INVENTED,
        source=dict(frames.provenance),
    )


def _run(world, parent=None, *, load_side_frame=None, **overrides):
    kwargs = dict(
        parameters=world.params,
        parent=parent or world.parent,
        data_provenance=INVENTED,
        registration_pointer=None,
        load_cohort_inputs=lambda: world.frames,
        load_side_frame=load_side_frame or world.spy([]),
        cola_rates=world.cola,
        provenance_kind=INVENTED,
        source=dict(world.frames.provenance),
    )
    kwargs.update(overrides)
    return mb.run_group_breakdowns(**kwargs)


@pytest.fixture(scope="module")
def world():
    params, cola = invented.invented_parameters()
    frames = _frames()
    reexecution = _reexecute(frames, params, cola)
    parent = common.CommittedArtifact(
        document=common.json_normalized(dict(reexecution.result))
    )
    loader = mb.invented_group_attribute_loader(frames, seed=SIDE_FRAME_SEED)
    calls: list[list[int]] = []

    def spy(record):
        def load(person_ids):
            record.append(list(person_ids))
            return loader(person_ids)

        return load

    state = SimpleNamespace(
        params=params,
        cola=cola,
        frames=frames,
        reexecution=reexecution,
        parent=parent,
        loader=loader,
        calls=calls,
        spy=spy,
    )
    state.document = _run(state, load_side_frame=spy(calls))
    return state


@pytest.fixture(scope="module")
def pieces(world):
    """The group work's objects, computed directly on the same
    re-execution (the run returns only the document)."""

    universe = [int(p) for p in world.reexecution.cohort.persons["person_id"]]
    side_frame = world.loader(universe)
    attributes = mb.person_attributes(
        world.reexecution,
        world.params,
        side_frame,
        tax_rates=g2.load_oasdi_tax_rates(),
        interest_rates=g2.load_trust_fund_interest_rates(),
    )
    assignment = mb.assign(attributes)
    breakdowns = mb.tabulate_breakdowns(
        world.reexecution,
        assignment,
        data_provenance=INVENTED,
        registration_pointer=None,
        parent_sha256=None,
    )
    return SimpleNamespace(
        side_frame=side_frame,
        attributes=attributes,
        assignment=assignment,
        breakdowns=breakdowns,
    )


# =========================================================================
# The document
# =========================================================================
def test_the_document_is_labelled_invented_post_hoc_and_report_only(world):
    document = world.document
    assert document["header"] == common.INVENTED_DATA_HEADER
    assert document["data_provenance"] == INVENTED
    assert document["blind"] is False
    assert document["scored"] is False
    assert document["publishes_regardless"] is True
    labels = document["labels"]
    assert labels[0] == g3.INVENTED_DATA_LABEL
    assert labels[1 : 1 + len(OUTPUT_LABELS)] == list(OUTPUT_LABELS)
    assert labels[-2:] == list(common.POST_HOC_LABELS)
    assert document["breakdown"]["post_hoc_labels"] == list(
        common.POST_HOC_LABELS
    )
    json.dumps(document, allow_nan=False)


def test_every_row_option_and_d430_is_broken_down(world):
    breakdowns = world.document["breakdowns"]
    assert list(breakdowns) == [*REGISTERED_ROWS, mb.SENSITIVITY_KEY]
    for options in breakdowns.values():
        assert list(options) == [str(n) for n in TABLE6_OPTIONS]
        for number, cell in options.items():
            assert cell["indicator_column"] == f"receives_{number}"
            assert cell["scored"] is False
            assert [d["key"] for d in cell["dimensions"]] == [
                d.key for d in mb.SCHEME.dimensions
            ]


def test_the_reproduction_is_exact_and_complete(world):
    reproduction = world.document["reproduction"]
    assert reproduction["identical"] is True
    assert reproduction["comparison"]["tolerance"] is None
    names = [check["name"] for check in reproduction["checks"]]
    assert all(check["identical"] for check in reproduction["checks"])
    assert all(
        check["n_leaves_compared"] > 0 for check in reproduction["checks"]
    )
    expected = {
        "parameters",
        "inputs.source.psid_files_sha256",
        "pipeline.rows",
        "pipeline.cohort_structure",
        "pipeline.sensitivities",
        f"group_rows.{mb.SENSITIVITY_KEY}.tabulation",
        f"group_rows.{mb.SENSITIVITY_KEY}.diagnostics",
    }
    for row in REGISTERED_ROWS:
        expected |= {
            f"group_rows.{row}.tabulation",
            f"group_rows.{row}.diagnostics",
        }
    assert expected <= set(names)
    # Every block the pipeline returns is compared, but the two the
    # registered runner replaced.
    pipeline_keys = {
        n.split(".", 1)[1] for n in names if n.startswith("pipeline.")
    }
    assert pipeline_keys == set(world.reexecution.result) - {
        "header",
        "specification",
    }


def test_the_loader_is_called_once_with_the_universe(world):
    assert len(world.calls) == 1
    assert world.calls[0] == [
        int(p) for p in world.reexecution.cohort.persons["person_id"]
    ]


def test_the_registered_cells_are_reproduced_by_g3(world):
    consistency = world.document["consistency_with_registered_cells"]
    assert consistency["identical"] is True
    assert consistency["n_checks"] == (
        (len(REGISTERED_ROWS) + 1) * len(TABLE6_OPTIONS) * 3
    )


def test_what_is_not_computed_says_why(world):
    not_computed = world.document["not_computed"]
    assert set(not_computed["dimensions"]) == {
        "poverty_status",
        "household_income_quintile",
    }
    assert all(
        reason.startswith("not computed:")
        for reason in not_computed["dimensions"].values()
    )
    statistics = not_computed["statistics"]
    assert statistics["mint8_benefit_statistics"]["statistics"] == list(
        g3.MINT_BENEFIT_STATISTICS
    )
    assert statistics["mint8_poverty_statistics"]["statistics"] == list(
        g3.POVERTY_STATISTICS
    )
    dimensions = {d.key for d in mb.SCHEME.dimensions}
    assert not dimensions & set(not_computed["dimensions"])


def test_the_scheme_is_mint8_with_lifetime_less_what_is_not_computed():
    full = [d.key for d in g3.MINT8_ANNUAL_WITH_LIFETIME_SCHEME.dimensions]
    kept = [d.key for d in mb.SCHEME.dimensions]
    assert kept == [k for k in full if k not in mb.NOT_COMPUTED_DIMENSIONS]
    by_key = {
        d.key: d for d in g3.MINT8_ANNUAL_WITH_LIFETIME_SCHEME.dimensions
    }
    for dimension in mb.SCHEME.dimensions:
        assert [c.label for c in dimension.categories] == [
            c.label for c in by_key[dimension.key].categories
        ]
    assert set(mb.COLUMNS_MAP) == set(kept) - {"total"}


# =========================================================================
# Invariants of the cells
# =========================================================================
def _result_cells(result: g3.GroupBreakdownResult):
    for dimension in result.dimensions:
        for cell in dimension.cells:
            yield dimension, cell


def test_categories_and_unclassified_partition_total(world, pieces):
    assignment = pieces.assignment
    for (key, number), result in pieces.breakdowns.items():
        rows = (
            world.reexecution.sensitivity_evaluation.rows
            if key == mb.SENSITIVITY_KEY
            else world.reexecution.evaluations[key].rows
        )
        weights = rows["weight"].to_numpy(dtype=float)
        receiving = rows[f"receives_{number}"].to_numpy(dtype=bool)
        total = result.cell("total", "total")
        for dimension in result.dimensions:
            if dimension.kind == g3.TOTAL:
                continue
            masks = [
                assignment.mask(dimension.key, cell.category)
                for cell in dimension.cells
            ]
            unclassified = assignment.unclassified_mask(dimension.key)
            stacked = np.vstack([*masks, unclassified])
            # disjoint and covering: every row in exactly one group
            assert (stacked.sum(axis=0) == 1).all()
            n = sum(c.counts["unweighted_n"] for c in dimension.cells)
            assert (
                n + dimension.unclassified["unweighted_n"]
                == total.counts["unweighted_n"]
            )
            w = math.fsum(
                [c.counts["weighted_n"] for c in dimension.cells]
                + [dimension.unclassified["weighted_n"]]
            )
            assert math.isclose(w, total.counts["weighted_n"], rel_tol=1e-12)
            numerators = [
                math.fsum(weights[mask & receiving]) for mask in masks
            ] + [math.fsum(weights[unclassified & receiving])]
            assert math.isclose(
                math.fsum(numerators),
                math.fsum(weights[receiving]),
                rel_tol=1e-12,
                abs_tol=1e-9,
            )


def test_every_share_is_the_direct_formula(world, pieces):
    """Differential: G3's cell against ``100 * fsum(w A) / fsum(w)``."""

    assignment = pieces.assignment
    compared = 0
    for (key, number), result in pieces.breakdowns.items():
        rows = (
            world.reexecution.sensitivity_evaluation.rows
            if key == mb.SENSITIVITY_KEY
            else world.reexecution.evaluations[key].rows
        )
        weights = rows["weight"].to_numpy(dtype=float)
        receiving = rows[f"receives_{number}"].to_numpy(dtype=bool)
        for dimension, cell in _result_cells(result):
            mask = (
                np.ones(len(rows), dtype=bool)
                if dimension.kind == g3.TOTAL
                else assignment.mask(dimension.key, cell.category)
            )
            statistic = cell.statistic(g3.SHARE)
            assert statistic.unweighted_n == int(mask.sum())
            if not mask.any():
                assert not statistic.defined
                continue
            expected = (
                100.0
                * math.fsum(weights[mask & receiving].tolist())
                / math.fsum(weights[mask].tolist())
            )
            assert statistic.defined
            assert statistic.value.hex() == expected.hex()
            compared += 1
    assert compared > 0


def test_total_and_sex_cells_equal_track_ms_cells(world, pieces):
    """Differential: G3 against ``tabulate_track_m``, recomputed here."""

    checks = mb.consistency_checks(world.reexecution, pieces.breakdowns)
    assert checks and all(check.identical for check in checks)


def test_shares_errors_and_floors_are_bounded(pieces):
    for result in pieces.breakdowns.values():
        for _, cell in _result_cells(result):
            statistic = cell.statistic(g3.SHARE)
            if not statistic.defined:
                continue
            assert 0.0 <= statistic.value <= 100.0
            se = statistic.uncertainty.get("design_se")
            if isinstance(se, dict):
                se = se.get("value")
            if se is not None:
                assert se >= 0.0
            floor = statistic.uncertainty.get("floor") or {}
            for name, value in floor.items():
                if isinstance(value, float) and name != "seeds":
                    assert value >= 0.0 or math.isnan(value)


def test_the_document_carries_the_same_cells(world, pieces):
    """The run's document holds the cells computed here, for every row."""

    for (key, number), result in pieces.breakdowns.items():
        document = result.as_dict()
        recorded = world.document["breakdowns"][key][str(number)]
        assert recorded["dimensions"] == common.json_normalized(
            document["dimensions"]
        )


# =========================================================================
# Attributes
# =========================================================================
def test_attributes_follow_the_rows(world, pieces):
    frame = pieces.attributes.frame
    rows = world.reexecution.evaluations["MS0"].rows
    assert frame["person_id"].tolist() == rows["person_id"].tolist()
    assert frame["weight"].tolist() == rows["weight"].tolist()
    assert frame["sex"].tolist() == rows["sex"].tolist()
    sensitivity = world.reexecution.sensitivity_evaluation.rows
    assert sensitivity["person_id"].tolist() == rows["person_id"].tolist()


def test_every_age_is_62_or_more_and_banded(pieces):
    frame = pieces.attributes.frame
    assert frame["age"].min() >= mb.YOUNGEST_AGE == 62
    long = pieces.assignment.long
    ages = long[long["dimension"] == "age"].sort_values("row_id")
    for age, label in zip(frame["age"], ages["label"], strict=True):
        band = (
            "90 or older"
            if age >= 90
            else f"{age // 10 * 10}–{age // 10 * 10 + 9}"
        )
        assert label == band


def test_codes_are_mint8s_or_declared_unclassified(pieces):
    frame = pieces.attributes.frame
    declared = pieces.attributes.unclassified_codes
    for code in frame["benefit_type"]:
        assert code in _BENEFIT_CODES or code in declared["benefit_type"]
    for code in frame["marital_status"]:
        assert code in common.MARITAL_STATUS_CODES or (
            code in declared["marital_status"]
        )
    assert set(declared["marital_status"]) <= {
        "unknown",
        "no_marriage_history",
    }


def test_the_aime_identity_is_exercised(pieces):
    record = pieces.attributes.provenance["initial_aime_at_62"]
    assert record["convention"]["equals_mint8_initial_aime_convention"]
    identity = record["identity_with_ms0_aime"]
    assert identity["all_equal"] is True
    assert identity["n_compared"] > 0


def test_persons_without_an_own_record_have_no_aime(world, pieces):
    frame = pieces.attributes.frame.set_index("person_id")
    persons = world.reexecution.cohort.persons
    without = [
        str(pid)
        for pid, own in zip(
            persons["person_id"], persons["own_record_id"], strict=True
        )
        if own is None or pd.isna(own)
    ]
    assert frame.loc[without, "initial_aime_at_62"].isna().all()


def test_quintiles_are_cut_within_each_birth_cohort(pieces):
    frame = pieces.attributes.frame
    long = pieces.assignment.long
    for key in (
        "initial_aime_quintile",
        "lifetime_payroll_tax_quintile",
        "lifetime_payroll_tax_quintile_shared",
    ):
        rows = long[long["dimension"] == key].sort_values("row_id")
        values = frame[mb.COLUMNS_MAP[key]].to_numpy(dtype=float)
        labels = rows["label"].to_numpy()
        assert (np.isnan(values) == (labels == g3.UNCLASSIFIED)).all()
        order = [c.label for c in mb.SCHEME.dimension(key).categories]
        rank = {label: 5 - i for i, label in enumerate(order)}
        for cohort_key in set(frame["birth_cohort_10y"]):
            inside = (
                frame["birth_cohort_10y"] == cohort_key
            ).to_numpy() & ~np.isnan(values)
            # A higher value never has a lower quintile in its cohort.
            pairs = sorted(
                zip(
                    values[inside],
                    [rank[x] for x in labels[inside]],
                    strict=True,
                )
            )
            ranks = [r for _, r in pairs]
            assert ranks == sorted(ranks)


def test_attributes_are_deterministic(world, pieces):
    again = mb.person_attributes(
        world.reexecution,
        world.params,
        pieces.side_frame,
        tax_rates=g2.load_oasdi_tax_rates(),
        interest_rates=g2.load_trust_fund_interest_rates(),
    )
    pd.testing.assert_frame_equal(again.frame, pieces.attributes.frame)
    assert common.compare_exact(
        "provenance", again.provenance, pieces.attributes.provenance
    ).identical


def test_a_side_frame_for_other_persons_is_refused(world, pieces):
    universe = [int(p) for p in world.reexecution.cohort.persons["person_id"]]
    short = world.loader(universe[1:])
    with pytest.raises(ValueError, match="exactly the universe"):
        mb.person_attributes(
            world.reexecution,
            world.params,
            short,
            tax_rates=g2.load_oasdi_tax_rates(),
            interest_rates=g2.load_trust_fund_interest_rates(),
        )


def test_side_frame_files_must_be_the_bytes_track_m_read(world, pieces):
    files = {"IND2023ER.txt": "1" * 64}
    reexecution = dataclasses.replace(
        world.reexecution,
        cohort_inputs=dataclasses.replace(
            world.frames,
            provenance={**world.frames.provenance, "psid_files_sha256": files},
        ),
    )
    side = dataclasses.replace(
        pieces.side_frame,
        provenance={
            **pieces.side_frame.provenance,
            "inputs": {"psid_files_sha256": {"IND2023ER.txt": "2" * 64}},
        },
    )
    with pytest.raises(ValueError, match="different bytes"):
        mb.person_attributes(
            reexecution,
            world.params,
            side,
            tax_rates=g2.load_oasdi_tax_rates(),
            interest_rates=g2.load_trust_fund_interest_rates(),
        )


def test_a_cohort_whose_2022_receipt_differs_is_refused(world):
    built = world.reexecution.cohort
    persons = built.persons.copy()
    persons.loc[0, "types_2022"] = "other"
    changed = dataclasses.replace(built, persons=persons)
    with pytest.raises(ValueError, match="rebuilt from the anchor"):
        mb._benefit_types(changed, world.frames, world.params.params)


# =========================================================================
# The order: nothing about groups before an exact reproduction
# =========================================================================
def _nudge(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return math.nextafter(value, math.inf)
    if isinstance(value, str):
        return value + "x"
    return 0


def _first_leaf(node: Any, kinds: tuple[type, ...]) -> list[Any] | None:
    """The key path to the first leaf of one of ``kinds`` under ``node``."""

    if isinstance(node, dict):
        for key in node:
            found = _first_leaf(node[key], kinds)
            if found is not None:
                return [key, *found]
        return None
    if isinstance(node, list):
        for index, item in enumerate(node):
            found = _first_leaf(item, kinds)
            if found is not None:
                return [index, *found]
        return None
    if (
        isinstance(node, kinds)
        and not isinstance(node, bool)
        or (bool in kinds and isinstance(node, bool))
    ):
        return []
    return None


def _tampered(parent, prefix, kinds=(float,)):
    document = copy.deepcopy(dict(parent.document))
    node = document
    for key in prefix:
        node = node[key]
    rest = _first_leaf(node, kinds)
    assert rest is not None, prefix
    path = [*prefix, *rest]
    holder = document
    for key in path[:-1]:
        holder = holder[key]
    holder[path[-1]] = _nudge(holder[path[-1]])
    return common.CommittedArtifact(document=document), path


def _cell(parent, row, key):
    cells = parent.document["rows"][row]["tabulation"]["cells"]
    index = next(i for i, c in enumerate(cells) if c["defined"])
    return ["rows", row, "tabulation", "cells", index, key]


TAMPERS: dict[str, Callable[[Any], tuple[list[Any], tuple[type, ...]]]] = {
    "ms0_share": lambda p: (_cell(p, "MS0", "share_percent"), (float,)),
    "ms4_design_se": lambda p: (_cell(p, "MS4", "design_se"), (float,)),
    "ms6_weighted_n": lambda p: (_cell(p, "MS6", "weighted_n"), (float,)),
    "ms2_unweighted_n": lambda p: (_cell(p, "MS2", "unweighted_n"), (int,)),
    "ms1_floor": lambda p: (_cell(p, "MS1", "floor"), (float,)),
    "ms3_diagnostics": lambda p: (["rows", "MS3", "diagnostics"], (int,)),
    "cohort_structure": lambda p: (["cohort_structure"], (int,)),
    "d430": lambda p: (["sensitivities", mb.SENSITIVITY_KEY], (float,)),
    "d430_cohort_structure": lambda p: (
        ["sensitivities", mb.SENSITIVITY_KEY, "cohort_structure"],
        (int,),
    ),
    "labels": lambda p: (["labels"], (str,)),
}


@pytest.mark.parametrize("name", list(TAMPERS))
def test_any_moved_committed_cell_refuses_before_any_group_work(
    world, monkeypatch, name
):
    """The re-execution itself is the fixture's (deterministic, and
    checked identical above); what is tested is that a parent differing
    in one leaf stops the run before the side frame is requested."""

    prefix, kinds = TAMPERS[name](world.parent)
    bad, path = _tampered(world.parent, prefix, kinds)
    monkeypatch.setattr(
        mb, "reexecute_track_m", lambda *a, **k: world.reexecution
    )
    calls: list[Any] = []
    with pytest.raises(common.ReproductionMismatchError) as error:
        _run(world, bad, load_side_frame=world.spy(calls))
    assert calls == []
    message = str(error.value)
    # The refusal names the differing block and path, never a value.
    leaf = "$" + "".join(
        f"[{key}]" if isinstance(key, int) else f".{key}" for key in path[1:]
    )
    assert f"pipeline.{path[0]}: 1 differing paths" in message
    assert repr(leaf) in message
    assert "refused before any group attribute or group cell" in message


def test_one_ulp_refuses_through_a_real_reexecution(world):
    """No stand-in: the run re-executes Track M on the INVENTED frames and
    refuses a parent whose MS0 share moved by one unit in the last place,
    before the side frame is requested."""

    bad, path = _tampered(
        world.parent, _cell(world.parent, "MS0", "share_percent")
    )
    calls: list[Any] = []
    with pytest.raises(
        common.ReproductionMismatchError, match="share_percent"
    ):
        _run(world, bad, load_side_frame=world.spy(calls))
    assert calls == []


def test_other_parameters_refuse_before_the_cohort_is_read(world):
    document = copy.deepcopy(dict(world.parent.document))
    document["parameters"]["oracle_pe_us_revision"] = "another"
    reads: list[int] = []

    def read():
        reads.append(1)
        return world.frames

    with pytest.raises(common.ReproductionMismatchError, match="parameters"):
        _run(
            world,
            common.CommittedArtifact(document=document),
            load_cohort_inputs=read,
        )
    assert reads == []


def test_other_psid_files_refuse_before_the_reexecution(world, monkeypatch):
    document = copy.deepcopy(dict(world.parent.document))
    document["inputs"]["source"]["psid_files_sha256"] = {"X.txt": "0" * 64}

    def never(*args, **kwargs):
        raise AssertionError("re-executed")

    monkeypatch.setattr(mb, "reexecute_track_m", never)
    with pytest.raises(common.ReproductionMismatchError, match="PSID files"):
        _run(world, common.CommittedArtifact(document=document))


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        (
            {"data_provenance": tabulation.REGISTERED_REAL},
            "own issue #42 registration pointer",
        ),
        (
            {
                "data_provenance": tabulation.REGISTERED_REAL,
                "registration_pointer": "https://example.org/42",
            },
            "own issue #42 registration pointer",
        ),
        (
            {
                "data_provenance": tabulation.REGISTERED_REAL,
                "registration_pointer": POINTER,
            },
            "reads psid_files records",
        ),
        ({"provenance_kind": PSID_FILES}, "invented records"),
        ({"data_provenance": "real"}, "unknown data_provenance"),
    ],
)
def test_mismatched_provenance_refuses_before_anything_is_read(
    world, overrides, match
):
    reads: list[int] = []
    with pytest.raises(ValueError, match=match):
        _run(
            world,
            load_cohort_inputs=lambda: reads.append(1),
            **overrides,
        )
    assert reads == []


def test_a_real_breakdown_needs_a_new_registration(world):
    document = dict(world.parent.document)
    parent = common.CommittedArtifact(
        document={**document, "registration_pointer": POINTER}
    )
    with pytest.raises(ValueError, match="must not be the parent run's"):
        _run(
            world,
            parent,
            data_provenance=tabulation.REGISTERED_REAL,
            registration_pointer=POINTER,
            provenance_kind=PSID_FILES,
        )


# =========================================================================
# The benefit type
# =========================================================================
_PARAMS = invented.invented_parameters()[0].params
_ITEM = st.sampled_from([True, False, None])


@settings(max_examples=400, deadline=None)
@given(
    st.fixed_dictionaries({name: _ITEM for name in ssr.SS_TYPES}),
    st.booleans(),
    st.sampled_from([None, cohort.BASIS_OLD_AGE, cohort.BASIS_DISABILITY]),
    st.integers(min_value=1913, max_value=1960),
    _ITEM,
)
def test_property_benefit_type(types, paid, basis, birth, other):
    if paid and basis is None:
        with pytest.raises(ValueError, match="own record"):
            mb.benefit_type_2022(
                types,
                birth_year=birth,
                paid_own_worker_benefit=paid,
                own_record_basis=basis,
                params=_PARAMS,
            )
        return

    def code(items):
        return mb.benefit_type_2022(
            items,
            birth_year=birth,
            paid_own_worker_benefit=paid,
            own_record_basis=basis,
            params=_PARAMS,
        )

    result = code(types)
    assert result in _BENEFIT_CODES or result.startswith("unclassified:")
    survivor = types["survivor"] is True
    dependent = (
        types["dependent_of_disabled"] is True
        or types["dependent_of_retired"] is True
    )
    if survivor and dependent:
        assert result == "unclassified:survivor_and_dependent_mentioned"
    elif survivor:
        assert result == "widower"
    elif dependent:
        assert result == "spousal"
    if result in ("retired_worker_only", "disabled_worker_only"):
        # "only": no auxiliary type mentioned or unknown, own benefit paid
        assert paid
        assert all(types[name] is False for name in ssr.AUXILIARY_TYPES)
    if result == "disabled_worker_only":
        assert 12 * (2022 - birth) < _PARAMS.fra_months(birth)
    # The 'other' item never decides the type.
    assert code({**types, "other": other}) == result


@pytest.mark.parametrize(
    ("mentioned", "basis", "birth", "expected"),
    [
        ({"retirement"}, cohort.BASIS_OLD_AGE, 1950, "retired_worker_only"),
        ({"retirement"}, cohort.BASIS_DISABILITY, 1958, "retired_worker_only"),
        (
            {"disability"},
            cohort.BASIS_DISABILITY,
            1958,
            "disabled_worker_only",
        ),
        # 2022 - 1950 = 72 is past the invented FRA: converted (MINT8)
        ({"disability"}, cohort.BASIS_DISABILITY, 1950, "retired_worker_only"),
        ({"disability"}, cohort.BASIS_OLD_AGE, 1958, "disabled_worker_only"),
        # neither or both worker types: the record's basis decides
        (set(), cohort.BASIS_DISABILITY, 1958, "disabled_worker_only"),
        ({"other"}, cohort.BASIS_OLD_AGE, 1958, "retired_worker_only"),
        (
            {"retirement", "disability"},
            cohort.BASIS_DISABILITY,
            1958,
            "disabled_worker_only",
        ),
        ({"retirement", "survivor"}, cohort.BASIS_OLD_AGE, 1950, "widower"),
        ({"dependent_of_retired"}, None, 1950, "spousal"),
    ],
)
def test_benefit_type_examples(mentioned, basis, birth, expected):
    types = {name: name in mentioned for name in ssr.SS_TYPES}
    paid = basis is not None
    assert (
        mb.benefit_type_2022(
            types,
            birth_year=birth,
            paid_own_worker_benefit=paid,
            own_record_basis=basis,
            params=_PARAMS,
        )
        == expected
    )


def test_an_unknown_auxiliary_item_leaves_only_unestablished():
    types = {name: False for name in ssr.SS_TYPES}
    types.update(retirement=True, survivor=None)
    assert (
        mb.benefit_type_2022(
            types,
            birth_year=1950,
            paid_own_worker_benefit=True,
            own_record_basis=cohort.BASIS_OLD_AGE,
            params=_PARAMS,
        )
        == "unclassified:auxiliary_item_unknown"
    )


def test_every_combination_of_known_items_is_placed():
    """Over all 64 known-item combinations, receipt and basis: the result
    is a code, and unclassified only for the named reasons."""

    reasons = set()
    for values in itertools.product([True, False], repeat=len(ssr.SS_TYPES)):
        types = dict(zip(ssr.SS_TYPES, values, strict=True))
        for paid, basis in (
            (True, cohort.BASIS_OLD_AGE),
            (True, cohort.BASIS_DISABILITY),
            (False, None),
        ):
            result = mb.benefit_type_2022(
                types,
                birth_year=1958,
                paid_own_worker_benefit=paid,
                own_record_basis=basis,
                params=_PARAMS,
            )
            if result.startswith("unclassified:"):
                reasons.add(result)
    assert reasons == {
        "unclassified:survivor_and_dependent_mentioned",
        "unclassified:no_own_worker_benefit",
    }


# =========================================================================
# Location fields: where a file was read is not what was read
# =========================================================================
_COLA_ELSEWHERE = "/elsewhere/checkout/" + mb.COLA_HISTORY_RELATIVE_PATH
_COLA_HERE = "/here/worktree/" + mb.COLA_HISTORY_RELATIVE_PATH


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (_COLA_ELSEWHERE, mb.COLA_HISTORY_RELATIVE_PATH),
        (mb.COLA_HISTORY_RELATIVE_PATH, mb.COLA_HISTORY_RELATIVE_PATH),
        ("/elsewhere/data/external/other.json", None),
        ("/elsewhere/xdata/external/ssa_cola_history.jsonx", None),
        (None, None),
        (3, None),
    ],
)
def test_relative_location(path, expected):
    assert mb.relative_location(path) == (
        path if expected is None else expected
    )


def _with_cola(document: dict, record: dict) -> dict:
    out = copy.deepcopy(document)
    out.setdefault("inputs", {}).setdefault("source", {})[
        "cola_history"
    ] = record
    return out


def test_located_changes_only_the_location_field():
    document = _with_cola({"x": 1.5}, {"path": _COLA_ELSEWHERE, "sha256": "a"})
    before = copy.deepcopy(document)
    out = mb.located(document)
    assert document == before
    assert out["inputs"]["source"]["cola_history"] == {
        "path": mb.COLA_HISTORY_RELATIVE_PATH,
        "sha256": "a",
    }
    assert out["x"] == 1.5
    assert mb.located({"x": 1}) == {"x": 1}


@pytest.mark.parametrize(
    ("recomputed", "identical"),
    [
        ({"path": _COLA_HERE, "sha256": "a"}, True),
        ({"path": _COLA_HERE, "sha256": "b"}, False),
        ({"path": "/here/data/external/another.json", "sha256": "a"}, False),
    ],
)
def test_the_cola_history_is_compared_by_bytes_not_location(
    world, recomputed, identical
):
    committed = _with_cola(
        dict(world.parent.document), {"path": _COLA_ELSEWHERE, "sha256": "a"}
    )
    reexecution = dataclasses.replace(
        world.reexecution,
        result=_with_cola(dict(world.reexecution.result), recomputed),
    )
    checks = {
        c.name: c for c in mb.reproduction_checks(reexecution, committed)
    }
    assert checks["pipeline.inputs"].identical is identical
    others = [c for name, c in checks.items() if name != "pipeline.inputs"]
    assert all(c.identical for c in others)


def test_the_document_records_the_location_rule(world):
    record = world.document["reproduction"]["location_fields"]
    assert record["fields"] == ["$.inputs.source.cola_history.path"]
    assert record["rule"] == mb.LOCATION_RULE
