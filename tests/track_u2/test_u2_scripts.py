"""The U2 entry points: dry run, structure, components, registered run.

* ``scripts/track_u2_dry_run.py`` runs end to end on INVENTED data into a
  temporary directory: every output headed INVENTED DATA - NOT A
  COMPARISON, all ten rows, the mapping and role branches and the
  required refusals.
* ``scripts/track_u2_structure.py`` and
  ``scripts/track_u2_component_diagnostics.py`` cannot reach the income
  concept or the tabulation (static transitive import graph, package
  initializers included), and refuse without Max's recorded
  authorization (``--authorized-by``) before any PSID path is resolved.
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
import functools
import importlib.util
import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

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
        # 2015-2023 resolved with the d637 commits for amendments 2, 5b
        # and 5a: the registry gate applies every wave's family records.
        assert not entry["registry_gate"]["refused"], wave
        assert not entry["registry_gate_dc_route"]["refused"], wave
    assert checks["mapping"]["negative_where_undocumented_refused"]["refused"]
    assert checks["mapping"]["crosswalk_as_input_refused"]["refused"]
    from populace_dynamics.uniform_cut_track_u2 import sources

    roles = checks["role_refusals"]
    # Section 16c (d1090): the registry context builds the invented
    # population exactly as the declared context does, exclusions included.
    built = roles["registry_context_on_invented_inputs"]
    assert not built["refused"]
    for row in ("U0", "U1"):
        assert built["rows"][row]["observations_equal"], row
        assert built["rows"][row]["dispositions_equal"], row
        exclusions = built["rows"][row]["family_unit_exclusions"]
        assert set(exclusions) == set(sources.FAMILY_UNIT_EXCLUSIONS)
        assert all(count > 0 for count in exclusions.values()), row
    # Amendment 1c (d637, confirmed by d745): both role contexts build a
    # code-88 first-year cohabitor's family with every observation and
    # disposition unchanged.
    for context in ("registry", "declared"):
        entry = roles[f"code_88_under_{context}_context"]
        assert not entry["refused"], context
        assert entry["observations_equal"], context
        assert entry["dispositions_equal"], context
        assert entry["rule"] == {
            "wave": 2019,
            "code": 88,
            "present": True,
            "income_role": "ofum",
            "spouse_slot": False,
            "legal_spouse_annuity": False,
            "marital_resolution": False,
            "administrative_birth_support": True,
            "refusal": None,
            "family_unit_exclusion": None,
        }, context
    assert roles["declared_context_on_non_invented_inputs"]["refused"]
    assert roles["registry_rules_equal_declared_where_resolved"]
    refusals = roles["registry_rule_refusals"]
    assert refusals and all(entry["refused"] for entry in refusals.values())
    # Only code 92's absence before 2017 refuses: code 88 takes amendment
    # 1c's convention since its registry commit.
    assert set(refusals) == {"2013.92", "2015.92"}
    # Both are absences, so no present relationship code refuses: the
    # count of invented members holding one is over no code.
    assert roles["invented_members_with_refused_codes"] == {}
    # No blocker remains, and an unfrozen load without Max's recorded
    # authorization refuses before any PSID path is resolved.
    assert not checks["loader_preflight"]["refused"]
    unauthorized = checks["unauthorized_unfrozen_load"]
    assert unauthorized["error"] == "U2AuthorizationRefusal"
    assert "needs Max's authorization" in unauthorized["message"]
    gate_refusals = checks["invented_gate_refusals"]
    assert set(gate_refusals) == {
        "relabel_as_invented",
        "hand_copied_invented_provenance",
        "frames_sealed_outside_the_generator",
        "other_frames_joined_to_an_invented_cohort",
        "declared_specs_on_survey_shaped_records",
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
        "duplicate_family_record_2019",
        "duplicate_person_record_2019",
        "code_88_in_excluded_unit_2019",
        "zero_weight_target_in_excluded_unit_2015",
        "sex_unknown_target_in_excluded_unit_2019",
        "spouse_slot_occupant_without_family_spouse_2019",
        "code_88_target_with_ofum_income_2019",
    ]
    assert all(entry["regenerated"] for entry in variants.values())
    # Amendment 1c: the two code-88 variants build under the declared
    # context (the cohabitor has the OFUM role).
    build_refused = {
        "missing_family_record_2019": "U2CohortError",
        "duplicate_family_record_2019": "U2CohortError",
        "duplicate_person_record_2019": "U2CohortError",
    }
    assert "repeats interview" in (
        variants["duplicate_family_record_2019"]["build"]["message"]
    )
    assert "repeats person_id" in (
        variants["duplicate_person_record_2019"]["build"]["message"]
    )
    income_refused = {
        # Two code-20 persons: no unique spouse-slot occupant to match the
        # family file's slot flag, so the income rows refuse.
        "ambiguous_legal_spouse": "U2CohortError",
        "spouse_slot_disagreement_2019": "U2CohortError",
        # Amendment 2 (d637): the family file's "no spouse" code never
        # removes the roster's occupant; the disagreement refuses.
        "spouse_slot_occupant_without_family_spouse_2019": "U2CohortError",
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
    round_1 = checks["round_1_refusals"]
    assert round_1["invented_individual_values_documented"] == 41
    assert round_1["pinned_parameters_pass_the_content_check"] is True
    expected_errors = {
        "undocumented_sex_code": "U2UndocumentedValue",
        "undocumented_relationship_code": "U2UndocumentedValue",
        "undocumented_relationship_rule": "U2RoleRefusal",
        "registered_preflight_without_evidence": "U2FrozenIdentityMismatch",
        "evidence_from_invented_inputs": "U2LoaderRefusal",
        "altered_threshold_under_the_pinned_label": "U2ParameterError",
    }
    assert {
        name: entry["error"]
        for name, entry in round_1.items()
        if isinstance(entry, dict)
    } == expected_errors
    round_2 = checks["round_2_refusals"]
    assert round_2["pinned_parameters_pass_the_typed_content_check"] is True
    assert {
        name: entry["error"]
        for name, entry in round_2.items()
        if isinstance(entry, dict)
    } == {
        "colliding_year_key_under_the_pinned_label": "U2ParameterError",
        "colliding_children_key_under_the_pinned_label": "U2ParameterError",
        "colliding_ssi_year_under_the_pinned_label": "U2ParameterError",
        "ssi_subclass_under_the_pinned_label": "U2ParameterError",
        "invented_run_naming_an_evidence_hash": "U2RunError",
    }
    round_3 = checks["round_3_refusals"]
    assert {name: entry["error"] for name, entry in round_3.items()} == {
        "registered_run_given_altered_row_definitions": "U2RunError",
        "registered_run_given_the_registered_rows": "U2RunError",
        "invented_run_naming_an_evidence_record": "U2RunError",
        "frame_container_not_a_plain_dict": "U2CohortError",
        "string_cell_not_exactly_a_str": "U2CohortError",
    }
    assert all(
        "row_set" in round_3[name]["message"]
        for name in (
            "registered_run_given_altered_row_definitions",
            "registered_run_given_the_registered_rows",
        )
    )
    assert "binds no" in (
        round_3["invented_run_naming_an_evidence_record"]["message"]
    )
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
    assert (
        "Loader source preflight passes at the committed registries "
        "(no blocker): True" in text
    )
    assert (
        "an unfrozen load without Max's recorded authorization refuses "
        "before any PSID path is resolved: True" in text
    )
    assert "Round-1 review refusals (invented;" in text
    assert "Round-2 review refusals (invented;" in text
    assert "Round-3 review refusals (invented):" in text
    assert "routes from other data to the invented declared rules" in text
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


#: The two section 20 step-4 entry points.
STRUCTURAL_SCRIPTS = ["track_u2_structure", "track_u2_component_diagnostics"]


def _probe(script, argv, tmp_path, *, resolve):
    """Run ``script`` with ``argv`` in a fresh interpreter: an audit hook
    records every open under the staged and the default PSID directory
    (the default pointed at a sentinel directory), and
    ``psid._resolve_data_dir`` records each call and, unless ``resolve``,
    raises.  Returns the exit code, stderr, the refusal, the opens and
    resolutions, and any poverty module loaded."""

    import os
    import subprocess
    import sys

    from populace_dynamics.data import psid

    data_dir = tmp_path / "psid"
    data_dir.mkdir(exist_ok=True)
    default = tmp_path / "default-psid"
    default.mkdir(exist_ok=True)
    watched = [str(data_dir), str(default), str(psid._DEFAULT_DATA_DIR)]
    path = ROOT / "scripts" / f"{script}.py"
    probe = f"""
import json, runpy, sys
opened, resolved = [], []
def spy(event, args):
    if event == "open" and args and any(
        str(args[0]).startswith(w) for w in {watched!r}
    ):
        opened.append(str(args[0]))
sys.addaudithook(spy)
from populace_dynamics.data import psid
original = psid._resolve_data_dir
def sentinel(data_dir):
    resolved.append(None if data_dir is None else str(data_dir))
    if not {resolve!r}:
        raise RuntimeError("a PSID path was resolved")
    return original(data_dir)
psid._resolve_data_dir = sentinel
sys.argv = [{str(path)!r}, *{argv!r}]
code, refusal = None, None
try:
    runpy.run_path({str(path)!r}, run_name="__main__")
except SystemExit as error:
    code = error.code
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
print(json.dumps({{"code": code, "refusal": refusal, "opened": opened,
                  "resolved": resolved, "forbidden": forbidden}}))
"""
    done = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, psid._DEFAULT_DATA_DIR_ENV: str(default)},
    )
    record = json.loads(done.stdout.strip().splitlines()[-1])
    record["stderr"] = done.stderr
    record["data_dir"] = str(data_dir)
    return record


@pytest.mark.parametrize("script", STRUCTURAL_SCRIPTS)
@pytest.mark.parametrize(
    "flags",
    [
        [],
        ["--data-dir", "{data_dir}"],
        ["--authorized-by", "yes"],
        ["--authorized-by", "D745"],
        ["--authorized-by", ""],
        ["--authorized-by", "d0", "--data-dir", "{data_dir}"],
    ],
)
def test_structural_pass_refuses_without_max_s_authorization(
    script, flags, tmp_path
):
    """Section 20 step 4 reads real PSID records, so it needs Max's
    authorization, recorded as a chief-of-staff decision: without
    ``--authorized-by <decision id>`` (or with anything but a decision
    id) each structural entry point, run in a fresh interpreter, exits
    non-zero before any PSID path is resolved or any file under the
    staged or default PSID directory is opened, with no poverty module
    loaded, and writes nothing."""

    output_dir = tmp_path / "out"
    data_dir = str(tmp_path / "psid")
    argv = ["--output-dir", str(output_dir)] + [
        flag.format(data_dir=data_dir) for flag in flags
    ]
    record = _probe(script, argv, tmp_path, resolve=False)
    assert record["code"] == 2, record
    assert record["refusal"] is None, record
    assert "needs Max's authorization" in record["stderr"]
    assert "does not grant" in record["stderr"]
    assert record["resolved"] == [] and record["opened"] == []
    assert record["forbidden"] == []
    assert not output_dir.exists()


@pytest.mark.parametrize("script", STRUCTURAL_SCRIPTS)
def test_an_authorized_structural_pass_reaches_the_loader(script, tmp_path):
    """With a decision id the pass gets past the authorization check and
    the source preflight (no blocker remains) and reaches the staged
    directory, where an empty one refuses at the cited-source rehash:
    nothing under it is opened and nothing is written.  The flag records
    the authorization; it grants nothing a decision id does not name."""

    output_dir = tmp_path / "out"
    data_dir = str(tmp_path / "psid")
    argv = [
        "--output-dir",
        str(output_dir),
        "--data-dir",
        data_dir,
        "--authorized-by",
        "d999999999",
    ]
    record = _probe(script, argv, tmp_path, resolve=True)
    assert record["refusal"][0] == "U2LoaderRefusal", record
    assert "is not staged" in record["refusal"][1]
    assert record["resolved"] == [data_dir]
    assert record["opened"] == []
    assert record["forbidden"] == []
    assert not output_dir.exists()


@pytest.mark.parametrize("script", STRUCTURAL_SCRIPTS)
def test_structural_build_refuses_without_an_authorization_record(
    script, monkeypatch
):
    """``build`` itself refuses without a valid record, or with one made
    at another git head, before the loader is called."""

    from populace_dynamics.uniform_cut_track_u2 import loader

    module = _script(script)
    calls = []
    monkeypatch.setattr(
        module.loader, "load_u2_inputs", lambda **kwargs: calls.append(kwargs)
    )
    for authorization in (None, {}, {"decision": "d745"}):
        with pytest.raises(loader.U2AuthorizationRefusal):
            module.build(authorization=authorization)
    elsewhere = loader.structural_pass_authorization("d745", git_head="f" * 40)
    with pytest.raises(loader.U2AuthorizationRefusal, match="another git"):
        module.build(authorization=elsewhere)
    assert calls == []


def test_the_component_pass_records_its_authorization(u2_inputs, monkeypatch):
    """The output records the decision id, the git head and the UTC time
    (here on invented inputs, with the import guard and the loader
    patched: no PSID path is touched)."""

    from populace_dynamics.uniform_cut_track_u2 import loader

    module = _script("track_u2_component_diagnostics")
    monkeypatch.setattr(module, "_leaked", lambda: [])
    monkeypatch.setattr(
        module.loader, "load_u2_inputs", lambda **kwargs: u2_inputs
    )
    record = loader.structural_pass_authorization(
        "d1234", git_head=module._git("rev-parse", "HEAD")
    )
    result = module.build(authorization=record)
    assert result["authorization"] == record


@pytest.mark.parametrize("script", STRUCTURAL_SCRIPTS)
def test_main_hands_build_the_recorded_authorization(
    script, tmp_path, monkeypatch
):
    module = _script(script)
    seen = {}

    def build(data_dir, *, authorization):
        seen.update(authorization)
        return {"authorization": authorization, "preregistration_evidence": {}}

    monkeypatch.setattr(module, "build", build)
    module.main(
        [
            "--output-dir",
            str(tmp_path),
            "--authorized-by",
            "d1234",
        ]
    )
    assert seen["decision"] == "d1234"
    assert seen["git_head"] == module._git("rev-parse", "HEAD")
    name = {
        "track_u2_structure": "track-u2-structure.json",
        "track_u2_component_diagnostics": (
            "track-u2-component-diagnostics.json"
        ),
    }[script]
    written = json.loads((tmp_path / name).read_text())
    assert written["authorization"] == seen


@pytest.mark.parametrize("script", STRUCTURAL_SCRIPTS)
def test_build_returns_the_authorization_in_its_output(script):
    """Statically: ``build`` puts the checked record in what it returns,
    under ``authorization`` (the structure pass cannot run to its end on
    invented inputs, whose seal its loader evidence refuses)."""

    tree = ast.parse((ROOT / "scripts" / f"{script}.py").read_text())
    (build,) = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build"
    ]
    returned = [
        node.value
        for node in ast.walk(build)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
    ]
    (output,) = returned
    pairs = {
        key.value: value
        for key, value in zip(output.keys, output.values, strict=True)
        if isinstance(key, ast.Constant)
    }
    assert isinstance(pairs["authorization"], ast.Name)
    assert pairs["authorization"].id == "authorization"
    first = build.body[0]
    assert ast.unparse(first) == (
        "authorization = "
        "loader.check_structural_pass_authorization(authorization)"
    )


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


@functools.cache
def _registered_module():
    return _script("run_track_u2_registered")


@pytest.fixture(scope="module")
def registered():
    return _registered_module()


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


#: INVENTED file digests standing in for the frozen PSID identities the
#: section 20 step-4 pass would record (no real file is hashed here).
_INVENTED_FILES = {
    "family/2013/FAM2013ER.txt": "1" * 64,
    "ind2023er/IND2023ER.txt": "2" * 64,
}


def _invented_evidence(**changes):
    from populace_dynamics.uniform_cut_track_u2 import cohort, loader, sources

    files = changes.pop("psid_files_sha256", _INVENTED_FILES)
    record = {
        "schema_version": loader.PREREGISTRATION_SCHEMA,
        "target_id": identity.TARGET_ID,
        "specification": identity.SPECIFICATION_ID,
        "registries_sha256": dict(sources.REGISTRY_SHA256),
        "cited_sources_sha256": {},
        "psid_files_sha256": dict(files),
        "psid_files_bundle_sha256": loader.files_bundle_sha256(files),
        "input_frames_sha256": "3" * 64,
        "frame_environment": cohort.frame_environment(),
    }
    record.update(changes)
    return record


def _preflight(registered, **overrides):
    kwargs = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": identity.ARTIFACT_PATH,
        "binding": "0" * 64,
        "git": _git(),
        "specification": _ratified_block(),
        "specification_sha256": "b" * 64,
        "evidence": _invented_evidence(),
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


def test_preflight_refuses_a_wrong_binding_then_checks_the_mapping(
    registered, monkeypatch
):
    with pytest.raises(ValueError, match="binds"):
        _preflight(registered)
    binding = registered.binding_sha256("b" * 64, _invented_evidence())
    from populace_dynamics.uniform_cut_track_u2 import loader, sources

    # Since amendment 1c's registry commit the mapping review passes at
    # the committed registries (with the invented specification and
    # evidence here; the committed ones refuse first, items 4 and 8) ...
    state = _preflight(registered, binding=binding)
    assert state["mapping_review"]["all_resolved"] is True
    assert state["binding_sha256"] == binding
    # ... and a blocker on any required entry refuses it.
    sources.RoleContext.from_registry()
    original = sources.blockers
    monkeypatch.setattr(
        sources,
        "blockers",
        lambda entry, name: (
            ["reblocked (test)"]
            if entry.get("id") == "2019.relationship.88"
            else original(entry, name)
        ),
    )
    with pytest.raises(loader.U2LoaderRefusal, match="^1 registry blockers"):
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
    from populace_dynamics.uniform_cut_track_u2 import cohort

    calls = []
    original = cohort.check_plan_against_support_registry

    def spy(registries):
        calls.append(registries.kind)
        return original(registries)

    monkeypatch.setattr(cohort, "check_plan_against_support_registry", spy)
    binding = registered.binding_sha256("b" * 64, _invented_evidence())
    assert _preflight(registered, binding=binding)["mapping_review"][
        "all_resolved"
    ]
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
    from populace_dynamics.uniform_cut_track_u2 import loader

    evidence = _invented_evidence()
    binding = registered.registration_binding("c" * 64, evidence)
    assert binding["target"] == identity.identity()
    assert [row["row"] for row in binding["rows"]] == list(rows.ROW_IDS)
    assert set(binding["plans"]) == {"U0", "U1"}
    assert binding["registries_sha256"]
    assert binding["parameters"]["ssi_sha256"].startswith("a58d55c1")
    assert binding["parameters"]["thresholds_sha256"].startswith("288399c4")
    assert binding["named_deltas"] == list(rows.NAMED_DELTAS)
    # Review round 1, finding 2: the frozen input identities are bound.
    assert binding["preregistration_evidence"] == {
        "sha256": loader.preregistration_evidence_sha256(evidence),
        "psid_files_sha256": dict(sorted(_INVENTED_FILES.items())),
        "psid_files_bundle_sha256": loader.files_bundle_sha256(
            _INVENTED_FILES
        ),
        "input_frames_sha256": "3" * 64,
    }
    assert registered.binding_sha256(
        "c" * 64, evidence
    ) != registered.binding_sha256("d" * 64, evidence)


def test_preflight_refuses_while_the_evidence_record_is_absent(registered):
    """Section 14: execution rechecks the frozen identities, so without
    the committed pre-registration evidence record (none exists at this
    commit) the preflight refuses before comparing the binding."""

    from populace_dynamics.uniform_cut_track_u2 import loader

    assert not loader.PREREGISTRATION_EVIDENCE_PATH.exists()
    with pytest.raises(loader.U2LoaderRefusal, match="no pre-registration"):
        _preflight(registered, evidence=None)
    with pytest.raises(loader.U2LoaderRefusal, match="registries other"):
        _preflight(
            registered,
            evidence=_invented_evidence(
                registries_sha256={
                    **_invented_evidence()["registries_sha256"],
                    "income": "0" * 64,
                }
            ),
        )


def test_a_binding_for_other_frozen_identities_refuses(registered):
    """A registration that quoted the binding of other frozen files or
    another frame digest does not match this evidence."""

    quoted = registered.binding_sha256("b" * 64, _invented_evidence())
    for other in (
        _invented_evidence(input_frames_sha256="4" * 64),
        _invented_evidence(
            psid_files_sha256={**_INVENTED_FILES, "ind2023er/x.sps": "5" * 64}
        ),
        _invented_evidence(
            psid_files_sha256={
                **_INVENTED_FILES,
                "ind2023er/IND2023ER.txt": "6" * 64,
            }
        ),
    ):
        with pytest.raises(ValueError, match="binds"):
            _preflight(registered, binding=quoted, evidence=other)


@settings(max_examples=100, deadline=None)
@given(
    key=st.sampled_from(sorted(_INVENTED_FILES) + ["frames"]),
    digest=st.text(alphabet="0123456789abcdef", min_size=64, max_size=64),
)
def test_the_binding_changes_with_every_frozen_identity(key, digest):
    """Invariant: changing any one frozen file hash or the frame digest
    changes the registration binding's SHA-256 (so a registration quotes
    exactly one set of frozen input identities)."""

    registered = _registered_module()
    base = _invented_evidence()
    if key == "frames":
        other = _invented_evidence(input_frames_sha256=digest)
        same = digest == base["input_frames_sha256"]
    else:
        other = _invented_evidence(
            psid_files_sha256={**_INVENTED_FILES, key: digest}
        )
        same = digest == _INVENTED_FILES[key]
    assert (
        registered.binding_sha256("b" * 64, other)
        == registered.binding_sha256("b" * 64, base)
    ) == same


@settings(max_examples=60, deadline=None)
@given(
    version=st.text(min_size=1, max_size=12),
    infer=st.booleans(),
)
def test_the_binding_changes_with_the_frame_environment(version, infer):
    """Invariant (#544): the binding covers the pandas settings the frame
    digest was taken under, through the evidence record's SHA-256: it
    changes exactly when the environment does (INVENTED environments)."""

    from populace_dynamics.uniform_cut_track_u2 import cohort

    registered = _registered_module()
    base = _invented_evidence()
    environment = {"pandas_version": version, "future_infer_string": infer}
    other = _invented_evidence(frame_environment=environment)
    same = environment == cohort.frame_environment()
    assert (
        registered.binding_sha256("b" * 64, other)
        == registered.binding_sha256("b" * 64, base)
    ) == same


def test_the_structure_pass_records_its_environment():
    """The step-4 pass's output records the interpreter and package
    versions it ran under, beside the frozen pandas settings, exactly as
    the registered run's sidecar records its own, so the one-shot can be
    run under the same ones (#544 review)."""

    import platform

    import pandas as pd

    module = _script("track_u2_structure")
    environment = module._environment()
    assert environment["python"] == platform.python_version()
    assert environment["packages"]["pandas"] == pd.__version__
    assert {"numpy", "pandas"} <= set(environment["packages"])
    # The same record the registered run's sidecar writes (two
    # implementations; the structure pass may not import the runner).
    assert environment == _registered_module()._environment()
    tree = ast.parse((ROOT / "scripts" / "track_u2_structure.py").read_text())
    (build,) = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build"
    ]
    (output,) = [
        node.value
        for node in ast.walk(build)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
    ]
    pairs = {
        key.value: value
        for key, value in zip(output.keys, output.values, strict=True)
        if isinstance(key, ast.Constant)
    }
    assert ast.unparse(pairs["environment"]) == "_environment()"


def test_the_registered_main_passes_the_evidence_to_the_loader(
    registered, monkeypatch
):
    """The one-shot reads PSID only through the loader with the frozen
    evidence the preflight bound (never an unfrozen load)."""

    from populace_dynamics.uniform_cut_track_u2 import loader

    evidence = loader.check_preregistration_evidence(_invented_evidence())
    calls = []

    class Stop(Exception):
        pass

    monkeypatch.setattr(
        registered,
        "preflight",
        lambda **kwargs: {"evidence": evidence, "params": None},
    )

    def load(**kwargs):
        calls.append(kwargs)
        raise Stop

    monkeypatch.setattr(loader, "load_u2_inputs", load)
    with pytest.raises(Stop):
        registered.main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--binding-sha256",
                "0" * 64,
                "--headline-row",
                "U0",
            ]
        )
    assert calls == [{"evidence": evidence}]


def test_the_registered_main_passes_the_bound_evidence_hash_to_the_run(
    registered, monkeypatch
):
    """Review rounds 2 and 3: ``main`` hands the run the evidence hash the
    preflight bound and the evidence record itself; the run compares the
    hash with the loader's seal and the frames and files with the record
    (``test_u2_loader.py``)."""

    from populace_dynamics.uniform_cut_track_u2 import loader

    bound = "e" * 64
    record = {"invented": True}
    params = object()
    inputs = object()
    calls = []

    class Stop(Exception):
        pass

    monkeypatch.setattr(
        registered,
        "preflight",
        lambda **kwargs: {
            "evidence": record,
            "params": params,
            "evidence_sha256": bound,
        },
    )
    monkeypatch.setattr(loader, "load_u2_inputs", lambda **kwargs: inputs)

    def run(*args, **kwargs):
        calls.append((args, kwargs))
        raise Stop

    monkeypatch.setattr(registered.runner, "run_track_u2", run)
    with pytest.raises(Stop):
        registered.main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--binding-sha256",
                "0" * 64,
                "--headline-row",
                "U0",
            ]
        )
    ((args, kwargs),) = calls
    assert args == (inputs, params)
    assert kwargs["preregistration_evidence_sha256"] == bound
    assert kwargs["preregistration_evidence"] is record
    assert "row_set" not in kwargs


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
