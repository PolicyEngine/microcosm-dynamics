"""Reproduction ordering, joins and population invariants on INVENTED data.

Synthetic parent cells here are INVENTED, never committed model outcomes.
The side loader uses G1's builder and the lifetime inputs are invented G2
rates. Property tests cover exact gating and fixed-category invariance.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
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
from populace_dynamics.group_breakdowns.common import (
    POSTHOC_LABELS,
    GroupBreakdownRefusal,
    assert_exact_cells,
    assert_sha256,
    environment,
    preflight,
    write_artifact_pair,
)
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


INVENTED_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-123456789"
)

INVENTED_COMMIT = "a" * 40

_SCALARS = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
)

_JSON = st.recursive(
    _SCALARS,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(), children, max_size=4),
    ),
    max_leaves=12,
)


def _invented_git(*args):
    return INVENTED_COMMIT if args == ("rev-parse", "HEAD") else ""


def _preflight(tmp_path, **overrides):
    arguments = {
        "registration_pointer": INVENTED_POINTER,
        "registered_commit": INVENTED_COMMIT,
        "output": tmp_path / "runs" / "invented_groups_posthoc_v1.json",
        "root": tmp_path,
        "git": _invented_git,
    }
    arguments.update(overrides)
    return preflight(**arguments)


@given(_JSON)
def test_exact_identity_after_json_round_trip(invented):
    """Every finite invented JSON tree reproduces all of its leaves."""

    restored = json.loads(json.dumps(invented, allow_nan=False))
    checked = assert_exact_cells(invented, restored)
    assert checked.compared_leaf_cells >= 0
    assert checked.absolute_tolerance == checked.relative_tolerance == 0.0


@given(_JSON, _JSON)
def test_identity_differential_against_canonical_json(left, right):
    """The independent JSON representation has the same exact semantics."""

    same = json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
        right, sort_keys=True, allow_nan=False
    )
    if same:
        assert_exact_cells(left, right)
    else:
        with pytest.raises(GroupBreakdownRefusal):
            assert_exact_cells(left, right)


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_one_binary64_step_never_gets_a_summation_tolerance(value):
    changed = math.nextafter(value, math.inf)
    with pytest.raises(GroupBreakdownRefusal):
        assert_exact_cells(
            {"invented_rate": value}, {"invented_rate": changed}
        )


@pytest.mark.parametrize(
    ("committed", "recomputed"),
    [
        (0.0, -0.0),
        (True, 1),
        (1, 1.0),
        ({"x": None}, {}),
        ({}, {"x": None}),
        ([1], [1, 2]),
        (float("nan"), float("nan")),
        (float("inf"), float("inf")),
        ({1: "x"}, {1: "x"}),
        (object(), object()),
    ],
)
def test_structural_and_nonfinite_mismatches_refuse(committed, recomputed):
    with pytest.raises(GroupBreakdownRefusal):
        assert_exact_cells(committed, recomputed)


def test_mapping_order_and_json_array_semantics():
    check = assert_exact_cells(
        {"a": (1, 2), "b": "x"}, {"b": "x", "a": [1, 2]}
    )
    assert check.compared_leaf_cells == 3


def test_mismatch_reports_path_without_cell_values():
    with pytest.raises(GroupBreakdownRefusal) as caught:
        assert_exact_cells({"invented": [123]}, {"invented": [456]})
    assert "cells.invented[0]" in str(caught.value)
    assert "123" not in str(caught.value)
    assert "456" not in str(caught.value)


def test_labels_state_the_post_hoc_report_only_status():
    assert POSTHOC_LABELS == (
        "registered, one-shot, post hoc, not blind",
        "report-only",
    )


def test_preflight_returns_bound_new_pair(tmp_path):
    result = _preflight(tmp_path)
    assert result.git_head == result.registered_commit == INVENTED_COMMIT
    assert result.git_clean
    assert result.output_path.name == "invented_groups_posthoc_v1.json"
    assert result.sidecar_path.name == "invented_groups_posthoc_v1.env.json"
    assert not result.output_path.exists()
    assert not result.sidecar_path.exists()


@pytest.mark.parametrize(
    "pointer",
    [
        "",
        INVENTED_POINTER.replace("/42#", "/41#"),
        INVENTED_POINTER.replace("https://", "http://"),
        INVENTED_POINTER.replace("microcosm-dynamics", "other-project"),
        INVENTED_POINTER + "?other=1",
        INVENTED_POINTER + "\n",
        INVENTED_POINTER.replace("#issuecomment-", "#discussioncomment-"),
    ],
)
def test_registration_pointer_refuses_before_git(tmp_path, pointer):
    def must_not_call_git(*args):
        pytest.fail("invalid pointer must refuse before reading git state")

    with pytest.raises(GroupBreakdownRefusal, match="issue #42"):
        _preflight(
            tmp_path, registration_pointer=pointer, git=must_not_call_git
        )


@pytest.mark.parametrize("commit", ["", "a" * 39, "A" * 40, "g" * 40])
def test_registered_commit_must_be_full_lowercase_sha(tmp_path, commit):
    with pytest.raises(GroupBreakdownRefusal, match="40-hex"):
        _preflight(tmp_path, registered_commit=commit)


def test_registered_commit_must_equal_head(tmp_path):
    with pytest.raises(GroupBreakdownRefusal, match="HEAD"):
        _preflight(tmp_path, registered_commit="b" * 40)


@given(st.text(min_size=1).filter(lambda value: bool(value.strip())))
def test_any_dirty_status_refuses_before_writing(status):
    """A tracked or untracked status has no permitted silent exception."""

    def dirty_git(*args):
        return INVENTED_COMMIT if args == ("rev-parse", "HEAD") else status

    with pytest.raises(GroupBreakdownRefusal, match="clean"):
        preflight(
            registration_pointer=INVENTED_POINTER,
            registered_commit=INVENTED_COMMIT,
            output=Path("invented_groups_posthoc_v1.json"),
            root=Path("INVENTED-NONEXISTENT-CHECKOUT"),
            git=dirty_git,
        )


@pytest.mark.parametrize(
    "relative",
    [
        "invented_groups_posthoc_v1.json",
        "runs/invented.json",
        "runs/subdirectory/invented_groups_posthoc_v1.json",
        "runs/../invented_groups_posthoc_v1.json",
        "runs/.invented_groups_posthoc_v1.json",
    ],
)
def test_output_must_be_a_named_artifact_in_checkout_runs(tmp_path, relative):
    with pytest.raises(GroupBreakdownRefusal, match="output must be"):
        _preflight(tmp_path, output=Path(relative))


@pytest.mark.parametrize("sidecar", [False, True])
def test_either_existing_member_blocks_registration(tmp_path, sidecar):
    path = tmp_path / "runs" / "invented_groups_posthoc_v1.json"
    path.parent.mkdir()
    if sidecar:
        path = path.with_suffix(".env.json")
    path.write_text("INVENTED existing bytes", encoding="utf-8")
    with pytest.raises(GroupBreakdownRefusal, match="one-shot"):
        _preflight(tmp_path)
    assert path.read_text(encoding="utf-8") == "INVENTED existing bytes"


def test_symlinked_runs_cannot_escape_checkout(tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    (tmp_path / "runs").symlink_to(target, target_is_directory=True)
    with pytest.raises(GroupBreakdownRefusal, match="symlink"):
        _preflight(tmp_path)


def test_dangling_sidecar_symlink_blocks_registration(tmp_path):
    output = tmp_path / "runs" / "invented_groups_posthoc_v1.json"
    output.parent.mkdir()
    output.with_suffix(".env.json").symlink_to(tmp_path / "absent")
    with pytest.raises(GroupBreakdownRefusal, match="one-shot"):
        _preflight(tmp_path)


def test_write_pair_binds_the_exact_artifact_bytes(tmp_path):
    output = tmp_path / "invented.json"
    written = write_artifact_pair(
        output=output,
        artifact={"header": "INVENTED DATA - NOT A COMPARISON", "x": 0.0},
        environment={"python": "INVENTED VERSION"},
    )
    assert written == (output, output.with_suffix(".env.json"))
    sidecar = json.loads(written[1].read_text(encoding="utf-8"))
    assert sidecar["artifact"] == output.name
    assert (
        sidecar["artifact_sha256"]
        == hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert sidecar["environment"] == {"python": "INVENTED VERSION"}


@pytest.mark.parametrize("sidecar", [False, True])
def test_write_collision_preserves_existing_member_and_removes_new(
    tmp_path, sidecar
):
    output = tmp_path / "invented.json"
    existing = output.with_suffix(".env.json") if sidecar else output
    existing.write_text("INVENTED original bytes", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_artifact_pair(output=output, artifact={"x": 1}, environment={})
    assert existing.read_text(encoding="utf-8") == "INVENTED original bytes"
    absent = output if sidecar else output.with_suffix(".env.json")
    assert not absent.exists()


@pytest.mark.parametrize("in_environment", [False, True])
def test_nonfinite_json_refuses_before_either_file_is_created(
    tmp_path, in_environment
):
    output = tmp_path / "invented.json"
    artifact = {} if in_environment else {"x": float("nan")}
    env = {"x": float("inf")} if in_environment else {}
    with pytest.raises(ValueError):
        write_artifact_pair(output=output, artifact=artifact, environment=env)
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


def test_failed_sidecar_open_rolls_back_new_artifact(tmp_path, monkeypatch):
    output = tmp_path / "invented.json"
    original_open = Path.open

    def failing_open(path, *args, **kwargs):
        if path == output.with_suffix(".env.json"):
            raise OSError("INVENTED storage failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(OSError, match="INVENTED storage failure"):
        write_artifact_pair(output=output, artifact={"x": 1}, environment={})
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


def test_environment_delegates_to_track_a_resolver(tmp_path):
    script = tmp_path / "scripts" / "run_track_a_registered.py"
    script.parent.mkdir()
    script.write_text(
        "def _environment(*, ssa_parameters_revision):\n"
        "    return {'delegated_revision': ssa_parameters_revision}\n"
        "def main():\n"
        "    raise AssertionError('registered main must not run')\n",
        encoding="utf-8",
    )
    assert environment(ssa_parameters_revision="INVENTED", root=tmp_path) == {
        "delegated_revision": "INVENTED"
    }


def test_sha_pin_refuses_changed_invented_artifact(tmp_path):
    path = tmp_path / "invented.json"
    path.write_bytes(b"INVENTED file")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert assert_sha256(path, digest) == digest
    path.write_bytes(b"INVENTED changed file")
    with pytest.raises(GroupBreakdownRefusal, match="SHA-256 mismatch"):
        assert_sha256(path, digest)


@pytest.mark.parametrize("digest", ["", "a" * 63, "A" * 64, "g" * 64])
def test_sha_pin_requires_full_lowercase_sha_before_file_read(
    tmp_path, digest
):
    with pytest.raises(GroupBreakdownRefusal, match="64-hex"):
        assert_sha256(tmp_path / "absent", digest)


def test_shared_comparison_apis_have_identical_strict_semantics():
    assert common.POSTHOC_LABELS == common.POST_HOC_LABELS
    assert common.INVENTED_HEADER == common.INVENTED_DATA_HEADER
    for expected, actual in ((0.0, -0.0), (True, 1), (1, 1.0)):
        checked = common.compare_exact("invented", expected, actual)
        assert not checked.identical
        with pytest.raises(common.GroupBreakdownRefusal):
            common.assert_exact_cells(expected, actual)
        assert (
            common._first_difference(actual, expected, "invented") is not None
        )
    for compare in (
        lambda: common.compare_exact("invented", {1: "x"}, {1: "x"}),
        lambda: common.assert_exact_cells({1: "x"}, {1: "x"}),
        lambda: common._first_difference({1: "x"}, {1: "x"}, "invented"),
    ):
        with pytest.raises(common.GroupBreakdownRefusal):
            compare()


def test_write_rollback_keeps_a_replacement_inode(tmp_path, monkeypatch):
    output = tmp_path / "invented.json"
    original_open = Path.open
    backup = tmp_path / "old-invented.json"

    def replace_before_failure(path, *args, **kwargs):
        if path == output.with_suffix(".env.json"):
            output.rename(backup)
            output.write_text("INVENTED replacement inode")
            raise OSError("INVENTED sidecar storage failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_before_failure)
    with pytest.raises(OSError, match="INVENTED sidecar"):
        common.write_artifact_pair(
            output=output, artifact={"x": 1}, environment={}
        )
    assert output.read_text() == "INVENTED replacement inode"
    assert backup.exists()
