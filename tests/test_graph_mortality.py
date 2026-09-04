"""Synthetic engineering tests for the optional population graph."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.graph.model import MortalityArtifact, fit_mortality
from populace_dynamics.graph.synthetic import write_synthetic_inputs


@pytest.fixture
def inputs(tmp_path):
    return write_synthetic_inputs(tmp_path / "inputs")


@pytest.fixture
def runtime():
    from populace_dynamics.graph._compat import require_graph

    try:
        require_graph()
    except ImportError as error:
        pytest.skip(str(error))
    from populace_dynamics.graph import runtime

    return runtime


def _read(path):
    return json.loads(path.read_text())


def _write(path, value):
    path.write_text(json.dumps(value))


def _fit(inputs):
    return fit_mortality(
        pd.DataFrame(_read(inputs["training"])),
        pd.DataFrame(_read(inputs["rates"])),
        boundary_year=2014,
        external_vintage_year=2014,
    )


def _run(runtime, inputs, tmp_path, **kwargs):
    return runtime.run_mortality_graph(
        **inputs, output_dir=tmp_path / "output", **kwargs
    )


def test_existing_mortality_fit_and_json_roundtrip(inputs):
    artifact = _fit(inputs)
    assert artifact.fit_rows == 8
    assert artifact.model.probability[("0+", "female")] == pytest.approx(
        -np.expm1(-0.25)
    )
    restored = MortalityArtifact.from_bytes(artifact.to_bytes())
    assert restored.to_bytes() == artifact.to_bytes()
    assert restored.model == artifact.model


def test_future_exposure_and_interview_information_are_excluded(inputs):
    baseline = _fit(inputs)
    training = _read(inputs["training"])
    training[-1]["death"] = 0.0
    _write(inputs["training"], training)
    assert _fit(inputs).to_bytes() == baseline.to_bytes()
    with pytest.raises(ValueError, match="vintage"):
        fit_mortality(
            pd.DataFrame(training),
            pd.DataFrame(_read(inputs["rates"])),
            boundary_year=2013,
            external_vintage_year=2014,
        )


@pytest.mark.parametrize("mutation", ["schema", "duplicate", "missing", "nan"])
def test_model_payload_fails_closed(inputs, mutation):
    raw = json.loads(_fit(inputs).to_bytes())
    if mutation == "schema":
        raw["schema_version"] = 99
    elif mutation == "duplicate":
        raw["probabilities"].append(copy.deepcopy(raw["probabilities"][0]))
    elif mutation == "missing":
        raw["probabilities"].pop()
    else:
        raw["probabilities"][0]["probability"] = float("nan")
    with pytest.raises(ValueError):
        MortalityArtifact.from_bytes(json.dumps(raw).encode())


def test_model_rejects_duplicate_json_members(inputs):
    payload = (
        _fit(inputs)
        .to_bytes()
        .replace(
            b'"schema_version":1', b'"schema_version":1,"schema_version":1'
        )
    )
    with pytest.raises(ValueError, match="duplicate"):
        MortalityArtifact.from_bytes(payload)


def test_graph_reuses_fit_and_reports_period_mass(runtime, inputs, tmp_path):
    cold = _run(runtime, inputs, tmp_path)
    warm = _run(runtime, inputs, tmp_path)
    assert cold.report["scope"] == "synthetic_engineering"
    assert cold.report["fixture_verdict"] == "pass"
    assert cold.report["engineering_verdict"] == "pass"
    assert all(node.hit for node in warm.manifest.nodes.values())
    assert cold.model_payload == warm.model_payload
    assert cold.report["mass"] == warm.report["mass"]
    mass = cold.report["mass"]
    assert mass["after"] == mass["before"] + mass["next_period"]
    assert mass["partition"]["stratum_before"]["2014"] == (
        mass["partition"]["stratum_after"]["2014"]
    )
    assert (tmp_path / "output" / "report.json").is_file()
    assert (tmp_path / "output" / "manifest.json").is_file()


def test_graph_matches_existing_steps_with_explicit_uniforms(
    runtime, inputs, tmp_path
):
    from populace_dynamics.engine.steps import (
        advance_age,
        apply_mortality,
    )

    result = _run(runtime, inputs, tmp_path)
    initial = pd.DataFrame(_read(inputs["initial"])).sort_values("person_id")
    initial["year"] = 2014
    uniforms = runtime.mortality_uniforms(initial.person_id.tolist())

    class FixedUniforms:
        def random(self, n):
            assert n == len(uniforms)
            return uniforms.copy()

    context = SimpleNamespace(rng_registry=None, year=2015, metadata={})
    model = MortalityArtifact.from_bytes(result.model_payload).model
    survived = apply_mortality(initial, context, FixedUniforms(), model=model)
    assert (
        survived.person_id.tolist()
        == initial.loc[
            uniforms >= model.probabilities(initial), "person_id"
        ].tolist()
    )
    expected = advance_age(survived, context, np.random.default_rng(0))
    actual = result.next_slice.sort_values("person_id")
    pd.testing.assert_frame_equal(
        actual[["person_id", "age", "year"]].reset_index(drop=True),
        expected[["person_id", "age", "year"]].reset_index(drop=True),
    )


def test_holdout_changes_only_evaluation_and_can_fail_fixture(
    runtime, inputs, tmp_path
):
    baseline = _run(runtime, inputs, tmp_path)
    holdout = _read(inputs["holdout"])
    for row in holdout["outcomes"]:
        row["death"] = 1
    _write(inputs["holdout"], holdout)
    changed = _run(runtime, inputs, tmp_path)
    assert changed.report["fixture_verdict"] == "fail"
    assert changed.report["engineering_verdict"] == "pass"
    assert changed.model_payload == baseline.model_payload
    for node_id in ("training", "fit", "initial", "apply", "advance", "age"):
        assert changed.manifest.nodes[node_id].hit
    assert not changed.manifest.nodes["evaluate"].hit
    pd.testing.assert_frame_equal(baseline.next_slice, changed.next_slice)


def test_recipient_edit_keeps_model_fit(runtime, inputs, tmp_path):
    baseline = _run(runtime, inputs, tmp_path)
    initial = _read(inputs["initial"])
    initial[0]["age"] += 1
    _write(inputs["initial"], initial)
    changed = _run(runtime, inputs, tmp_path)
    assert changed.manifest.nodes["fit"].hit
    assert changed.model_payload == baseline.model_payload
    assert not changed.manifest.nodes["apply"].hit


def test_training_weight_edit_invalidates_fit_and_application(
    runtime, inputs, tmp_path
):
    baseline = _run(runtime, inputs, tmp_path)
    training = _read(inputs["training"])
    training[0]["start_weight"] = 8.0
    _write(inputs["training"], training)
    changed = _run(runtime, inputs, tmp_path)
    assert not changed.manifest.nodes["fit"].hit
    assert not changed.manifest.nodes["apply"].hit
    assert changed.model_payload != baseline.model_payload


def test_stable_draws_are_row_chunk_and_unrelated_person_invariant(runtime):
    first = runtime.mortality_uniforms([11, 21, 31])
    np.testing.assert_array_equal(
        runtime.mortality_uniforms([31, 11, 21]), first[[2, 0, 1]]
    )
    np.testing.assert_array_equal(
        runtime.mortality_uniforms([1, 11, 21, 31])[1:], first
    )
    np.testing.assert_array_equal(
        np.concatenate(
            [
                runtime.mortality_uniforms([11]),
                runtime.mortality_uniforms([21, 31]),
            ]
        ),
        first,
    )


@pytest.mark.parametrize("identity", [None, 1.5, "1", True])
def test_mortality_draws_reject_noninteger_person_ids(runtime, identity):
    with pytest.raises(ValueError, match="identities"):
        runtime.mortality_uniforms([identity])


def test_population_reorder_and_unrelated_person_preserve_survivors(
    runtime, inputs, tmp_path
):
    baseline = _run(runtime, inputs, tmp_path)
    initial = _read(inputs["initial"])
    _write(inputs["initial"], initial[::-1])
    reordered = _run(runtime, inputs, tmp_path)
    pd.testing.assert_frame_equal(baseline.next_slice, reordered.next_slice)
    initial.append({"person_id": 1, "age": 44, "sex": "male", "weight": 2.0})
    _write(inputs["initial"], initial)
    holdout = _read(inputs["holdout"])
    holdout["outcomes"].append(
        {"person_id": 1, "year": 2015, "age": 45, "death": 0}
    )
    _write(inputs["holdout"], holdout)
    extended = _run(runtime, inputs, tmp_path)
    pd.testing.assert_frame_equal(
        baseline.next_slice,
        extended.next_slice.query("person_id != 1").reset_index(drop=True),
    )


@pytest.mark.parametrize("all_die", [False, True])
def test_empty_or_complete_survivor_expansion(
    runtime, inputs, tmp_path, all_die
):
    training = _read(inputs["training"])
    for row in training:
        row["death"] = 1.0 if all_die else 0.0
        row["exposure"] = 1e-9 if all_die else 1.0
    _write(inputs["training"], training)
    result = _run(runtime, inputs, tmp_path)
    warm = _run(runtime, inputs, tmp_path)
    assert warm.manifest.nodes["advance"].hit
    assert len(result.next_slice) == (0 if all_die else 20)
    assert result.report["mass"]["next_period"] == (
        0.0 if all_die else result.report["mass"]["before"]
    )
    if all_die:
        assert (
            "2015" not in result.report["mass"]["partition"]["stratum_after"]
        )


def test_household_accounting_is_explicitly_unsupported(
    runtime, inputs, tmp_path
):
    with pytest.raises(ValueError, match="household"):
        _run(runtime, inputs, tmp_path, household_accounting=True)


def test_optional_entrypoint_has_actionable_missing_capability(monkeypatch):
    from populace_dynamics.graph import _compat

    monkeypatch.setattr(_compat, "_python_version", lambda: (3, 12))
    with pytest.raises(ImportError, match="Python >=3.13"):
        _compat.require_graph()


def test_optional_entrypoint_reports_old_core_capabilities(monkeypatch):
    from populace_dynamics.graph import _compat

    monkeypatch.setattr(_compat, "_python_version", lambda: (3, 14))
    monkeypatch.setattr(
        _compat.importlib, "import_module", lambda name: SimpleNamespace()
    )
    with pytest.raises(ImportError, match="typed model-artifact"):
        _compat.require_graph()


def test_cli_requires_output_directory():
    from populace_dynamics.graph.__main__ import parser

    with pytest.raises(SystemExit):
        parser().parse_args(["--synthetic"])


def test_keyed_kernel_hashes_random_coordinate_encoding(runtime, monkeypatch):
    from microcosm.graph import canonical

    _, registry = runtime.build_graph()
    kernel = registry.get("dynamics.mortality.apply@1")
    assert kernel.capabilities.dependencies == ("numpy", "pandas")
    before = kernel.implementation_hash()
    encoding_source = Path(canonical.__file__).resolve()
    original = Path.read_bytes

    def changed_source(path):
        payload = original(path)
        if path.resolve() == encoding_source:
            payload += b"\n# coordinate encoding change\n"
        return payload

    monkeypatch.setattr(Path, "read_bytes", changed_source)
    assert kernel.implementation_hash() != before
