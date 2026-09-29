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
  before reading PSID, with a fake ``git`` and hand-built specification
  blocks.  Its checks run in the script's own order (pointer, commit,
  clean checkout, output identity, one-shot outputs, specification, rows,
  rulings, named deltas, plan against the support registry, parameters,
  binding, mapping review); section 14 lists what must be verified before
  PSID is read, not an order, and every check here precedes the read.
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
    assert (
        _script("track_u2_dry_run").main(["--output-dir", str(directory)]) == 0
    )
    return directory


def test_every_dry_run_output_is_headed_invented(dry_run):
    result = json.loads((dry_run / "result.json").read_text())
    assert (
        result["header"]
        == DRY_RUN_HEADER
        == "INVENTED DATA - NOT A COMPARISON"
    )
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
    assert checks["identification"][
        "identical_births_and_annuitant_attributes"
    ]
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
    refusals = roles["registry_rule_refusals"]
    assert refusals and all(entry["refused"] for entry in refusals.values())
    for key in ("2015.20", "2019.90", "2021.92", "2023.90", "2013.88"):
        assert key in refusals, key
    members = roles["invented_members_with_refused_codes"]
    # The invented population holds a member of every refused code
    # except code 88, which the separate code-88 variant adds.
    for key, count in members.items():
        assert (count > 0) == (not key.endswith(".88")), key
    assert checks["loader_preflight"]["refused"]
    gate_refusals = checks["invented_gate_refusals"]
    assert set(gate_refusals) == {
        "relabel_as_invented",
        "hand_copied_invented_provenance",
        "unsealed_psid_files_label",
        "registry_context_with_declared_rules",
        "changed_registries_labelled_committed",
        "declared_gate_on_survey_shaped_records",
        "declared_gate_on_a_registered_run",
    }
    for name, entry in gate_refusals.items():
        assert entry["refused"], name
    variants = checks["invented_variants"]
    assert list(variants) == [
        "code_88_first_year_cohabitor",
        "missing_family_record_2019",
        "zero_weight_legal_spouse_2019",
        "ambiguous_legal_spouse",
        "spouse_slot_disagreement_2019",
        "missing_head",
    ]
    assert all(entry["regenerated"] for entry in variants.values())
    build_refused = {
        "code_88_first_year_cohabitor": "U2RoleRefusal",
        "missing_family_record_2019": "U2CohortError",
    }
    income_refused = {
        # Two code-20 persons: no unique spouse-slot occupant to match the
        # family file's slot flag, so the income rows refuse.
        "ambiguous_legal_spouse": "U2CohortError",
        "spouse_slot_disagreement_2019": "U2CohortError",
        "missing_head": "AdjustedPovertyError",
    }
    for name, entry in variants.items():
        if name in build_refused:
            assert entry["build"]["error"] == build_refused[name], name
            continue
        assert not entry["build"]["refused"], name
        assert entry["income"]["refused"] == (name in income_refused), name
        if name in income_refused:
            assert entry["income"]["error"] == income_refused[name], name
    assert (
        variants["ambiguous_legal_spouse"]["legal_spouse_pairing"]["ambiguous"]
        > 0
    )
    assert variants["missing_head"]["legal_spouse_pairing"]["no_head"] > 0
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
        assert entry["per_observation"] == checks["invariants"][row_id]
        assert (
            entry["cells_full_sample"]
            and entry["cells_both_halves_every_seed"]
        )
    assert checks["invariants"]["U3"]["n_ssi_new_positive"] > 0
    branches = checks["row_branches"]
    assert set(branches) == {*rows.ROW_IDS[1:], "real_interest_rate_0.02"}
    for name, entry in branches.items():
        if name == "U1":
            assert entry["n_birth_years_u1"] == 10
            assert entry["n_observations_u1"] > entry["n_observations_u0"]
        else:
            assert entry["n_changed_from_u0"] > 0, name


def test_dry_run_markdown_names_the_refusals(dry_run):
    text = (dry_run / "RESULTS.md").read_text()
    assert "INVENTED" in text
    assert "not a comparison" in text.lower()
    assert "Loader preflight refuses" in text
    assert "Routes from other data to the invented declared rules" in text
    assert "Named invented variants" in text
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
    package = (
        name.split(".") if path.name == "__init__.py" else name.split(".")[:-1]
    )
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
def test_pre_registration_scripts_refuse_before_opening_psid(script, tmp_path):
    """Section 20 step 4 is not authorized and the registries hold open
    routes: each structural entry point, run in a fresh interpreter,
    refuses in the loader's source preflight before any file under the
    PSID directory is opened, with no poverty module loaded, and writes
    nothing."""

    import subprocess
    import sys

    data_dir = tmp_path / "psid"
    data_dir.mkdir()
    output_dir = tmp_path / "out"
    path = ROOT / "scripts" / f"{script}.py"
    probe = f"""
import json, runpy, sys
opened = []
def spy(event, args):
    if event == "open" and args and str(args[0]).startswith({str(data_dir)!r}):
        opened.append(str(args[0]))
sys.addaudithook(spy)
sys.argv = [{str(path)!r}, "--output-dir", {str(output_dir)!r},
            "--data-dir", {str(data_dir)!r}]
refusal = None
try:
    runpy.run_path({str(path)!r}, run_name="__main__")
except BaseException as error:
    refusal = [type(error).__name__, str(error)]
forbidden = [
    name for name in (
        "populace_dynamics.estimates.adjusted_poverty",
        "populace_dynamics.uniform_cut_track_u2.estimator",
        "populace_dynamics.uniform_cut_track_u2.tabulation",
    )
    if name in sys.modules
]
print(json.dumps({{"refusal": refusal, "opened": opened,
                  "forbidden": forbidden}}))
"""
    done = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    record = json.loads(done.stdout.strip().splitlines()[-1])
    assert record["refusal"][0] == "U2LoaderRefusal", record
    assert "registry blockers" in record["refusal"][1]
    assert record["opened"] == []
    assert record["forbidden"] == []
    assert not output_dir.exists()


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
    block["ssi"]["parameters"][
        "sha256"
    ] = "a58d55c160b48cd3e21f730d45265374bd3c8a9eb7eae947469a5a5dc0b23762"
    block["income_concept"]["employer_dc"]["reader"] = "u2_employer_dc_adapter"
    block["income_concept"]["employer_dc"][
        "later_wave_mapping_status"
    ] = "RESOLVED"
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
def test_preflight_refuses_before_the_specification(
    registered, overrides, message
):
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
def test_preflight_refuses_incomplete_specifications(
    registered, change, message
):
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


def test_preflight_refuses_a_plan_the_support_registry_does_not_hold(
    registered, monkeypatch
):
    """Review finding 10: the registered preflight holds row U1's plan
    (and so U0's) equal to the committed support registry before the
    binding is even compared."""

    from populace_dynamics.uniform_cut_track_u2 import cohort

    monkeypatch.setattr(cohort, "EVEN_BIRTH_YEARS", (1946, 1948, 1950, 1952))
    with pytest.raises(cohort.U2CohortError, match="support registry"):
        _preflight(registered)


def test_preflight_checks_the_plan_before_the_mapping_review(
    registered, monkeypatch
):
    from populace_dynamics.uniform_cut_track_u2 import cohort, loader

    calls = []
    original = cohort.check_plan_against_support_registry

    def spy(registries):
        calls.append(registries.kind)
        return original(registries)

    monkeypatch.setattr(cohort, "check_plan_against_support_registry", spy)
    binding = registered.binding_sha256("b" * 64)
    with pytest.raises(loader.U2LoaderRefusal, match="registry blockers"):
        _preflight(registered, binding=binding)
    # Once in the preflight, once again in the loader's source preflight.
    assert calls == ["committed", "committed"]


def test_existing_artifact_or_sidecar_refuses(registered, monkeypatch):
    artifact = identity.ARTIFACT_PATH
    sidecar = identity.SIDECAR_PATH
    original = Path.exists
    for existing in (artifact, sidecar):

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
