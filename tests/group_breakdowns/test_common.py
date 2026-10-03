"""Reproduction ordering, joins and population invariants on INVENTED data.

Synthetic parent cells here are INVENTED, never committed model outcomes.
The side loader uses G1's builder and the lifetime inputs are invented G2
rates. Property tests cover exact gating and fixed-category invariance.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a.config import REGISTERED_ROWS, TrackAConfig
from populace_dynamics.estimates import group_breakdown as g3
from populace_dynamics.group_breakdowns import common
from populace_dynamics.track_a_v2.invented import invented_parameters

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "projection_groups_dry_run.py"
)
_SPEC = importlib.util.spec_from_file_location("_invented_groups", _SCRIPT)
dry = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dry)


def _case():
    """Four INVENTED people, two draws; one person is under age60."""
    persons = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4],
            "birth_year": [1940, 1950, 1965, 1980],
            "weight": [1.0, 2.0, 3.0, 4.0],
        }
    )
    cohort = SimpleNamespace(
        persons=persons,
        careers={
            pid: {year: 10000.0 * pid for year in range(2000, 2011)}
            for pid in (1, 2, 3, 4)
        },
        start_year=2010,
        anchor_wave=2011,
        data_provenance="invented",
        labels=(
            common.INVENTED_HEADER,
            "PSID-seeded closed cohort",
            "Python oracle (not Axiom)",
            "fixed-path mechanical incidence",
        ),
    )
    config = TrackAConfig(rows=("R0",), draw_indices=(0, 1))
    rows = []
    states = []
    for draw in config.draw_indices:
        for pid, birth, weight in persons.itertuples(index=False, name=None):
            amount = 10000.0 * pid
            kind = "disabled_worker" if pid == 4 else "retired_worker"
            rows.append(
                {
                    "draw": draw,
                    "person_id": pid,
                    "family_unit_id": pid,
                    "birth_year": birth,
                    "age_reference": 2030 - birth,
                    "weight": weight,
                    "beneficiary_base": True,
                    "beneficiary_reform": True,
                    "benefit_base": amount,
                    "benefit_reform": amount * 0.9,
                    "benefit_components": {
                        kind: {"base": amount, "reform": amount * 0.9}
                    },
                }
            )
            states.append(
                {
                    "draw": draw,
                    "person_id": pid,
                    "sex": "female" if pid % 2 else "male",
                    "marital_status": (
                        "widowed",
                        "divorced",
                        "never_married",
                        "married",
                    )[pid - 1],
                }
            )
    result = {
        "labels": list(cohort.labels),
        "config": config.as_dict(),
        "rows": {
            "R0": {
                "row": REGISTERED_ROWS["R0"].as_dict(),
                "tabulation": {"groups": [{"cell": -10.0}]},
            }
        },
        "draws": {"2011": {"0": {"n": 4}, "1": {"n": 4}}},
    }
    replay = common.ProjectionReplay(
        "cola",
        result,
        {"R0": pd.DataFrame(rows)},
        {2011: pd.DataFrame(states)},
    )
    inputs = SimpleNamespace(
        cohort=cohort, additional_cohorts=(), params=invented_parameters()
    )
    return replay, copy.deepcopy(result), inputs, config


def _options():
    # No marriage history is supplied in this fixture; this is unavailable,
    # rather than an assumption that every INVENTED person is unmarried.
    options = dry.invented_lifetime_options({})
    return replace(options, marriage_episode_loader=None)


def _run(replay, parent, inputs, config, **kwargs):
    return common.run_group_breakdown(
        replay,
        parent,
        inputs=inputs,
        config=config,
        attribute_loader=dry.invented_attribute_loader,
        lifetime_options=_options(),
        **kwargs,
    )


@pytest.fixture(scope="module")
def report():
    return _run(*_case())


@pytest.mark.parametrize("field", ("cell", "draw", "labels", "row", "missing"))
def test_every_mismatch_refuses_before_any_loader_and_writes_nothing(
    tmp_path, monkeypatch, field
):
    replay, parent, inputs, config = _case()
    if field == "cell":
        parent["rows"]["R0"]["tabulation"]["groups"][0]["cell"] = -9.0
    elif field == "draw":
        parent["draws"]["2011"]["1"]["n"] = 5
    elif field == "labels":
        parent["labels"].append("INVENTED mutation")
    elif field == "row":
        parent["rows"]["R0"]["row"]["anchor_wave"] = 2009
    else:
        del parent["draws"]

    def forbidden(*args, **kwargs):
        pytest.fail(
            "group attribute/measure loader called before reproduction"
        )

    monkeypatch.setattr(common.g1, "load_group_attributes", forbidden)
    monkeypatch.setattr(common.g2, "initial_aime_at_62", forbidden)
    monkeypatch.setattr(common.g3, "assign_groups", forbidden)
    with pytest.raises(common.ReproductionMismatch):
        common.run_group_breakdown(
            replay, parent, inputs=inputs, config=config
        )
    assert not list(tmp_path.iterdir())


@settings(max_examples=25, deadline=None)
@given(
    st.floats(
        min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
    )
)
def test_exact_float_gate_has_no_tolerance(value):
    replay, parent, _, _ = _case()
    replay.result["rows"]["R0"]["tabulation"]["groups"][0]["cell"] = value
    parent["rows"]["R0"]["tabulation"]["groups"][0]["cell"] = value
    assert common.verify_reproduction(replay, parent)["identical"]
    parent["rows"]["R0"]["tabulation"]["groups"][0]["cell"] = value + 1.0
    with pytest.raises(common.ReproductionMismatch, match="cell"):
        common.verify_reproduction(replay, parent)


def test_outputs_use_g3_labels_statistics_and_population_variants(report):
    variants = report["rows"]["R0"]["variants"]
    assert variants["test_population"]["input_summary"]["n_rows"] == 8
    assert variants["mint_population"]["input_summary"]["n_rows"] == 6
    for variant in variants.values():
        assert set(g3.MINT_BENEFIT_STATISTICS) <= set(variant["statistics"])
        assert g3.RATIO_OF_SCENARIO_MEANS in variant["statistics"]
        dimensions = {d["key"]: d for d in variant["dimensions"]}
        for dimension in g3.MINT8_SCHEME.dimensions:
            assert [
                cell["label"] for cell in dimensions[dimension.key]["cells"]
            ] == list(dimension.labels)
        assert common.POST_HOC_LABELS[0] in variant["labels"]
        assert "report-only" in variant["labels"]
        assert "poverty_status" in variant["not_computed"]
        assert (
            "no household income" in variant["not_computed"]["poverty_status"]
        )
        for dimension in variant["dimensions"]:
            assert dimension["ssa_subgroup_suppressed"]
    json.dumps(report, allow_nan=False)


def test_projected_marital_states_and_lifetime_unavailability(report):
    assignment = report["rows"]["R0"]["variants"]["test_population"][
        "assignment"
    ]
    dimensions = {d["key"]: d for d in assignment["dimensions"]}
    assert dimensions["marital_status"]["n_by_category"] == {
        "married": 2,
        "divorced": 2,
        "widowed": 2,
        "never_married": 2,
    }
    assert (
        dimensions["lifetime_payroll_tax_quintile_shared"]["n_unclassified"]
        == 8
    )
    assert (
        report["lifetime_provenance"]["2011"][
            "lifetime_payroll_tax_quintile_shared"
        ]["reason"]
        == "marriage history not supplied"
    )
    assert report["reproduction"]["absolute_tolerance"] == 0


def test_g3_total_differential_after_adapter_join(report):
    replay, _, inputs, config = _case()
    total_scheme = g3.derive_scheme(
        g3.MINT8_SCHEME,
        scheme_id="invented_total",
        title="INVENTED total",
        drop=tuple(
            d.key for d in g3.MINT8_SCHEME.dimensions if d.key != g3.TOTAL_KEY
        ),
    )
    rows = replay.benefit_rows["R0"]
    assignment = g3.assign_groups(
        rows, total_scheme, {}, key_columns=("draw", "person_id")
    )
    direct = g3.tabulate_projection_breakdown(
        rows,
        assignment,
        data_provenance="invented",
        config=common.ColaAgeProfileConfig(draw_indices=config.draw_indices),
        labels=inputs.cohort.labels,
        post_hoc_labels=common.POST_HOC_LABELS,
    ).as_dict()
    actual = report["rows"]["R0"]["variants"]["test_population"]["dimensions"][
        0
    ]
    assert actual == direct["dimensions"][0]


@settings(max_examples=12, deadline=None)
@given(st.integers(min_value=1, max_value=100), st.permutations((0, 1, 2, 3)))
def test_fixed_lifetime_categories_preserve_weight_scaling_and_person_order(
    scale, order
):
    _, _, inputs, _ = _case()
    cohort = inputs.cohort
    original, _ = common._lifetime_side(cohort, inputs.params, _options())
    changed = copy.copy(cohort)
    changed.persons = cohort.persons.iloc[list(order)].copy()
    changed.persons["weight"] *= scale
    actual, _ = common._lifetime_side(changed, inputs.params, _options())
    pd.testing.assert_frame_equal(
        original.sort_values("person_id").reset_index(drop=True),
        actual.sort_values("person_id").reset_index(drop=True),
    )


@pytest.mark.parametrize(
    "mapping,expected",
    (
        ({"retired_worker": 10}, "retired_worker_only"),
        ({"disabled_worker": 10}, "disabled_worker_only"),
        ({"retired_worker": 10, "spouse": 2}, "spousal"),
        ({"retired_worker": 10, "aged_widow": 2}, "widower"),
        ({"disabled_widow": 10}, "widower"),
        ({"retired_worker": 0}, None),
    ),
)
def test_current_law_benefit_mapping_includes_dual_entitlement(
    mapping, expected
):
    assert (
        common.benefit_type(
            {k: {"base": v, "reform": 999} for k, v in mapping.items()}
        )
        == expected
    )


def test_inconsistent_components_refuse():
    with pytest.raises(ValueError, match="concurrent"):
        common.benefit_type(
            {"retired_worker": {"base": 1}, "disabled_worker": {"base": 1}}
        )
    with pytest.raises(ValueError, match="unknown"):
        common.benefit_type({"other": {"base": 1}})


@pytest.mark.parametrize("amount", (-1, float("nan"), float("inf"), True))
def test_invalid_baseline_components_refuse(amount):
    with pytest.raises(ValueError, match="finite nonnegative"):
        common.benefit_type({"retired_worker": {"base": amount}})


@pytest.mark.parametrize("frame_kind", ("benefits", "states"))
def test_retained_frames_are_sealed_before_attribute_loading(
    frame_kind, monkeypatch
):
    replay, parent, inputs, config = _case()
    if frame_kind == "benefits":
        replay.benefit_rows["R0"].loc[0, "benefit_base"] = 1.0
    else:
        replay.states[2011].loc[0, "sex"] = "male"

    def forbidden(*args, **kwargs):
        pytest.fail("attribute loader called on tampered replay")

    monkeypatch.setattr(common.g1, "load_group_attributes", forbidden)
    with pytest.raises(common.ReproductionMismatch, match="frames changed"):
        common.run_group_breakdown(
            replay, parent, inputs=inputs, config=config
        )


def test_duplicate_or_missing_attribute_people_refuse():
    replay, parent, inputs, config = _case()

    def missing(person_ids, **kwargs):
        return dry.invented_attribute_loader(person_ids[:-1], **kwargs)

    with pytest.raises(ValueError, match="retain each opening person"):
        common.run_group_breakdown(
            replay,
            parent,
            inputs=inputs,
            config=config,
            attribute_loader=missing,
            lifetime_options=_options(),
        )


@pytest.mark.parametrize("pointer", (None, "invalid", "parent"))
def test_real_metadata_requires_new_pointer_before_group_loaders(
    pointer, monkeypatch
):
    # Only INVENTED person rows exist; the real-data metadata is a refusal
    # fixture and cannot reach an attribute, measure or outcome function.
    replay, parent, inputs, config = _case()
    inputs.cohort.data_provenance = "registered_real"
    old = "https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-1"
    parent["registration_pointer"] = old

    def forbidden(*args, **kwargs):
        pytest.fail("group loader reached without a new registration")

    monkeypatch.setattr(common.g1, "load_group_attributes", forbidden)
    with pytest.raises(ValueError, match="registration|pointer"):
        common.run_group_breakdown(
            replay,
            parent,
            inputs=inputs,
            config=config,
            registration_pointer=old if pointer == "parent" else pointer,
        )


@pytest.mark.parametrize(
    "changes", ({"draw_indices": (0,)}, {"floor_seeds": (0, 1)})
)
def test_group_configuration_cannot_depart_from_verified_replay(
    changes, monkeypatch
):
    replay, parent, inputs, config = _case()

    def forbidden(*args, **kwargs):
        pytest.fail(
            "attribute loader reached with changed group configuration"
        )

    monkeypatch.setattr(common.g1, "load_group_attributes", forbidden)
    with pytest.raises(common.ReproductionMismatch, match="configuration"):
        common.run_group_breakdown(
            replay, parent, inputs=inputs, config=replace(config, **changes)
        )
