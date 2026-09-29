"""The U2 entry points: dry run, structure, components, registered run.

* ``scripts/track_u2_dry_run.py`` runs end to end on INVENTED data into a
  temporary directory: every output headed INVENTED DATA - NOT A
  COMPARISON, all ten rows, the mapping and role branches and the
  required refusals.
* ``scripts/track_u2_structure.py`` and
  ``scripts/track_u2_component_diagnostics.py`` cannot reach the income
  concept or the tabulation (static transitive import graph, package
  initializers included).
* ``scripts/run_track_u2_registered.py`` refuses every other state
  before reading PSID, in the section 14 preflight order, with a fake
  ``git`` and hand-built specification blocks.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from populace_dynamics.uniform_cut_track_u2 import (
    DRY_RUN_HEADER,
    identity,
    rows,
)

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
COMMIT = "a" * 40


def _script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def dry_run(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("track_u2_dry_run")
    assert _script("track_u2_dry_run").main(["--output-dir", str(directory)]) == 0
    return directory


def test_every_dry_run_output_is_headed_invented(dry_run):
    result = json.loads((dry_run / "result.json").read_text())
    assert result["header"] == DRY_RUN_HEADER == "INVENTED DATA - NOT A COMPARISON"
    assert result["labels"][0] == DRY_RUN_HEADER
    text = (dry_run / "RESULTS.md").read_text()
    assert text.splitlines()[0] == f"# {DRY_RUN_HEADER}"
    assert result["cohort_provenance"]["kind"] == "invented"
    assert result["parameters"]["thresholds"]["kind"] == "invented"
    assert result["psid_files_sha256"] == {}
    assert list(result["rows"]) == list(rows.ROW_IDS)


def test_dry_run_records_every_branch_and_refusal(dry_run):
    result = json.loads((dry_run / "result.json").read_text())
    checks = result["checks"]
    assert checks["specification_rows"]["rows_equal_the_block"]
    assert checks["named_deltas"]["equal_to_section_12"]
    assert checks["u2_rulings_against_block"]["refused"]
    assert checks["plans"]["u0_pairs"] == 5
    assert checks["plans"]["u1_pairs"] == 15
    assert checks["plans"]["u1_birth_years"] == 10
    assert checks["plans"]["wave_2013_cells"] == [[1946, 2013, 2012, 66, 0.5]]
    assert checks["identification"]["identical_births_and_annuitant_attributes"]
    for wave, entry in checks["mapping"]["by_wave"].items():
        assert entry["round_trip_equal"], wave
        assert entry["income_equal_to_invented_frame"], wave
        assert entry["dc_equal_to_invented_frame"], wave
        assert entry["wealth1_identity"]["n_exact"] == entry["n_records"]
        assert entry["registry_gate"]["refused"] == (wave != "2013")
        assert entry["registry_gate_dc_route"]["refused"] == (wave != "2013")
    assert checks["mapping"]["negative_where_undocumented_refused"]["refused"]
    assert checks["mapping"]["crosswalk_as_input_refused"]["refused"]
    roles = checks["role_refusals"]
    assert roles["registry_context_on_invented_inputs"]["refused"]
    assert roles["code_88_under_declared_context"]["refused"]
    assert roles["declared_context_on_non_invented_inputs"]["refused"]
    assert roles["registry_rules_equal_declared_where_resolved"]
    assert checks["loader_preflight"]["refused"]
    assert checks["registered_guard_refuses_invented_inputs"]["refused"]
    assert checks["registered_parameter_check_refuses_invented_thresholds"][
        "refused"
    ]
    assert all(v["refused"] for v in checks["cross_cohort_refusals"].values())
    for row_id, entry in checks["invariants"].items():
        for key, value in entry.items():
            if not key.startswith("n_"):
                assert value is True, (row_id, key)
    for row_id, entry in result["monotonicity"].items():
        assert entry["cells_full_sample"] and entry["cells_both_halves_every_seed"]
    assert checks["invariants"]["U3"]["n_ssi_new_positive"] > 0


def test_dry_run_markdown_names_the_refusals(dry_run):
    text = (dry_run / "RESULTS.md").read_text()
    assert "INVENTED" in text
    assert "not a comparison" in text.lower()
    assert "Loader preflight refuses" in text
    for delta in rows.NAMED_DELTAS:
        assert f"- {delta}." in text


# ---------------------------------------------------------------------------
# Structure and component entry points: no poverty import
# ---------------------------------------------------------------------------
def _modules() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for base, prefix in ((ROOT / "src", ()), (ROOT / "scripts", ("scripts",))):
        for path in base.rglob("*.py"):
            parts = (*prefix, *path.relative_to(base).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts:
                out[".".join(parts)] = path
    return out


def _imports(name: str, path: Path, modules: dict[str, Path]) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = name.split(".") if path.name == "__init__.py" else name.split(".")[:-1]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - node.level + 1]
                if node.module:
                    base = [*base, *node.module.split(".")]
                root = ".".join(base)
            else:
                root = node.module or ""
            found.add(root)
            found.update(f"{root}.{alias.name}" for alias in node.names)
    internal = set()
    for item in found:
        parts = item.split(".")
        internal.update(
            ".".join(parts[:n])
            for n in range(1, len(parts) + 1)
            if ".".join(parts[:n]) in modules
        )
    return internal


def _reachable(root: str) -> set[str]:
    modules = _modules()
    seen: set[str] = set()
    pending = [root]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        pending.extend(_imports(name, modules[name], modules) - seen)
    return seen


@pytest.mark.parametrize(
    "script", ["track_u2_structure", "track_u2_component_diagnostics"]
)
def test_pre_registration_scripts_cannot_reach_the_poverty_computation(script):
    reachable = _reachable(f"scripts.{script}")
    forbidden = set(_script(script).FORBIDDEN_MODULES)
    assert "populace_dynamics.estimates.adjusted_poverty" in forbidden
    assert "populace_dynamics.uniform_cut_track_u2.estimator" in forbidden
    assert not forbidden & reachable, sorted(forbidden & reachable)
    assert "populace_dynamics.uniform_cut_track_u2.loader" in reachable


# ---------------------------------------------------------------------------
# Registered entry point
# ---------------------------------------------------------------------------
def _git(head: str = COMMIT, porcelain: str = ""):
    def fake(*args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return porcelain
        raise AssertionError(args)

    return fake


@pytest.fixture(scope="module")
def registered():
    return _script("run_track_u2_registered")


def _ratified_block():
    block = copy.deepcopy(rows.specification_block())
    block["status"] = "ratified_frozen"
    block["version"] = "u2-ratified-1"
    block["blocked_by"] = []
    block["ssi"]["parameters"]["sha256"] = (
        "a58d55c160b48cd3e21f730d45265374bd3c8a9eb7eae947469a5a5dc0b23762"
    )
    block["income_concept"]["employer_dc"]["reader"] = "u2_employer_dc_adapter"
    block["income_concept"]["employer_dc"]["later_wave_mapping_status"] = (
        "RESOLVED"
    )
    block["decisions"] = {
        "ruled_by": "Max",
        "ruled_on": "2026-09-28",
        **copy.deepcopy(rows.U2_RULINGS),
    }
    return block


def _preflight(registered, **overrides):
    kwargs = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": identity.ARTIFACT_PATH,
        "binding": "0" * 64,
        "git": _git(),
        "specification": _ratified_block(),
        "specification_sha256": "b" * 64,
    }
    kwargs.update(overrides)
    return registered.preflight(**kwargs)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"registration_pointer": "https://example.org/x"}, "issue #42"),
        ({"registered_commit": "abc"}, "full 40-hex"),
        ({"git": _git(head="b" * 40)}, "is not the registered commit"),
        ({"git": _git(porcelain=" M x")}, "clean"),
        (
            {"output": identity.U1_ARTIFACT_PATH},
            "U1 specification or artifact",
        ),
        ({"output": ROOT / "runs" / "other.json"}, "not U2's artifact"),
    ],
)
def test_preflight_refuses_before_the_specification(registered, overrides, message):
    with pytest.raises(ValueError, match=message):
        _preflight(registered, **overrides)


def test_preflight_refuses_the_draft_specification(registered):
    with pytest.raises(ValueError, match="draft|ratified"):
        _preflight(registered, specification=rows.specification_block())


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda b: b.update(blocked_by=["x"]), "blocked"),
        (
            lambda b: b["ssi"]["parameters"].update(sha256="TO_VERIFY"),
            "TO_VERIFY",
        ),
        (
            lambda b: b["threshold"].update(capture_status="pending_capture"),
            "pending|captured",
        ),
        (
            lambda b: b["population"]["headline"].update(fallback_row="U1"),
            "fixed U0",
        ),
        (lambda b: b["decisions"].pop("downloads"), "differ"),
        (lambda b: b.update(target_id="U1"), "not 'U2'"),
    ],
)
def test_preflight_refuses_incomplete_specifications(registered, change, message):
    block = _ratified_block()
    change(block)
    with pytest.raises(ValueError, match=message):
        _preflight(registered, specification=block)


def test_preflight_refuses_a_wrong_binding_then_the_open_mapping(registered):
    with pytest.raises(ValueError, match="binds"):
        _preflight(registered)
    binding = registered.binding_sha256("b" * 64)
    from populace_dynamics.uniform_cut_track_u2 import loader

    with pytest.raises(loader.U2LoaderRefusal, match="registry blockers"):
        _preflight(registered, binding=binding)


def test_existing_artifact_or_sidecar_refuses(registered, monkeypatch):
    artifact = identity.ARTIFACT_PATH
    sidecar = identity.SIDECAR_PATH
    for existing in (artifact, sidecar):
        original = Path.exists

        def exists(path, existing=existing):
            if path in (artifact, sidecar):
                return path == existing
            return original(path)

        monkeypatch.setattr(Path, "exists", exists)
        with pytest.raises(ValueError) as error:
            _preflight(registered)
        assert str(error.value) == (
            f"{artifact} already exists: the registered run is one-shot"
        )
        monkeypatch.setattr(Path, "exists", original)


def test_binding_covers_every_registered_identity(registered):
    binding = registered.registration_binding("c" * 64)
    assert binding["target"] == identity.identity()
    assert [row["row"] for row in binding["rows"]] == list(rows.ROW_IDS)
    assert set(binding["plans"]) == {"U0", "U1"}
    assert binding["registries_sha256"]
    assert binding["parameters"]["ssi_sha256"].startswith("a58d55c1")
    assert binding["parameters"]["thresholds_sha256"].startswith("288399c4")
    assert binding["named_deltas"] == list(rows.NAMED_DELTAS)
    assert registered.binding_sha256("c" * 64) != registered.binding_sha256(
        "d" * 64
    )


def test_registered_headline_choice_is_only_u0(registered):
    with pytest.raises(SystemExit):
        registered.main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--binding-sha256",
                "0" * 64,
                "--headline-row",
                "U0-F",
            ]
        )
