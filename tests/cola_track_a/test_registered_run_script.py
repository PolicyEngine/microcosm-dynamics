"""The registered one-shot entry point refuses every non-registered state.

No PSID file is read and no statistic is computed here: only the preflight
guards of ``scripts/run_track_a_registered.py`` run, with a fake ``git``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
COMMIT = "a" * 40
#: A ratified A1 block header, as committed (a1-ratified-1).
RATIFIED = {"status": "ratified_frozen", "version": "a1-ratified-1"}


def _script():
    path = ROOT / "scripts" / "run_track_a_registered.py"
    spec = importlib.util.spec_from_file_location("_registered_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(head: str = COMMIT, porcelain: str = ""):
    def fake(*args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return porcelain
        raise AssertionError(args)

    return fake


def test_the_registered_state_passes(tmp_path):
    state = _script().preflight(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "run.json",
        git=_git(),
        specification=RATIFIED,
    )
    assert state == {"head": COMMIT}


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"registration_pointer": "https://example.org/x"}, "issue #42"),
        # Another issue whose number starts with 42.
        (
            {
                "registration_pointer": (
                    "https://github.com/PolicyEngine/microcosm-dynamics/"
                    "issues/420#issuecomment-1"
                )
            },
            "issue #42",
        ),
        # The issue itself, not a registration comment on it.
        (
            {
                "registration_pointer": (
                    "https://github.com/PolicyEngine/microcosm-dynamics/"
                    "issues/42"
                )
            },
            "issue #42",
        ),
        ({"registered_commit": "abc123"}, "full 40-hex"),
        ({"registered_commit": "g" * 40}, "full 40-hex"),
        ({"git": _git(head="b" * 40)}, "is not the registered commit"),
        ({"git": _git(porcelain=" M src/x.py")}, "clean"),
        # The pre-ratification A1 block (a1-ratified-candidate-1).
        (
            {
                "specification": {
                    "status": (
                        "ratification_candidate_rulings_recorded_not_merged"
                    ),
                    "version": "a1-ratified-candidate-1",
                }
            },
            "authorizes no run",
        ),
        (
            {"specification": {**RATIFIED, "version": "a1-draft-3"}},
            "authorizes no run",
        ),
    ],
    ids=[
        "pointer",
        "other-issue",
        "issue-not-comment",
        "short-sha",
        "non-hex-sha",
        "wrong-head",
        "dirty-tree",
        "a1-candidate",
        "a1-draft",
    ],
)
def test_non_registered_states_are_refused(tmp_path, kwargs, match):
    arguments = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": tmp_path / "run.json",
        "git": _git(),
        "specification": RATIFIED,
        **kwargs,
    }
    with pytest.raises(ValueError, match=match):
        _script().preflight(**arguments)


@pytest.mark.parametrize("existing", ["run.json", "run.env.json"])
def test_an_existing_artifact_refuses_a_second_shot(tmp_path, existing):
    (tmp_path / existing).write_text("{}")
    with pytest.raises(ValueError, match="one-shot"):
        _script().preflight(
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "run.json",
            git=_git(),
            specification=RATIFIED,
        )


def test_the_artifact_is_created_exclusively(tmp_path):
    # A file that appears after the preflight is never overwritten.
    target = tmp_path / "run.json"
    _script()._write_new(target, "first\n")
    with pytest.raises(FileExistsError):
        _script()._write_new(target, "second\n")
    assert target.read_text() == "first\n"


def test_the_registration_pointer_and_commit_are_required():
    with pytest.raises(SystemExit):
        _script().main([])


def test_the_committed_specification_is_ratified():
    # The committed A1 block passes the check a registered run applies.
    from populace_dynamics.cola_track_a.runner import a1_parameter_block

    block = a1_parameter_block()
    _script().check_specification_ratified(block)
    assert {block["status"], block["version"]} == {
        RATIFIED["status"],
        RATIFIED["version"],
    }


def test_a_null_status_is_refused(tmp_path):
    # str(None) is "None", which carries no unratified marker; a missing or
    # null status or version must still refuse.
    for specification in (
        {**RATIFIED, "status": None},
        {"version": RATIFIED["version"]},
    ):
        with pytest.raises(ValueError, match="authorizes no run"):
            _script().preflight(
                registration_pointer=POINTER,
                registered_commit=COMMIT,
                output=tmp_path / "run.json",
                git=_git(),
                specification=specification,
            )


def test_the_preflight_and_a7_share_one_ratification_test():
    from populace_dynamics.estimates import cola_age_profile

    script = _script()
    assert script.UNRATIFIED_MARKERS is cola_age_profile.UNRATIFIED_MARKERS


def _project() -> dict:
    import tomllib

    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    return {"name": project["name"], "version": project["version"]}


def test_the_sidecar_resolves_each_import_to_its_distribution():
    # The registered run's sidecar recorded null for "policyengine-us" and
    # "populace-dynamics": neither is an installed distribution name.  The
    # sidecar now resolves each import name to the distributions that
    # provide it and records no unresolved name.
    import importlib.metadata

    environment = _script()._environment(ssa_parameters_revision="INVENTED")
    packages = environment["packages"]
    assert None not in packages.values()
    assert all(
        isinstance(version, str) and version for version in packages.values()
    )
    assert not {"populace-dynamics", "policyengine-us"} & set(packages)
    by_import = environment["distributions_by_import"]
    assert set(by_import) == set(_script().ENV_IMPORTS)
    for name in ("numpy", "pandas", "scipy"):
        assert by_import[name] == [name]
        assert packages[name] == importlib.metadata.version(name)
    project = _project()
    assert environment["project"] == project
    installed = importlib.metadata.packages_distributions()
    assert by_import["populace_dynamics"] == sorted(
        set(installed.get("populace_dynamics", ()))
    )
    for distribution in by_import["populace_dynamics"]:
        assert distribution == project["name"]
        assert packages[distribution] == importlib.metadata.version(
            distribution
        )
    assert environment["populace_dynamics_source"] == "src/populace_dynamics"
    oracle = environment["policyengine_us_parameters"]
    assert oracle["revision"] == "INVENTED"
    assert "git checkout" in oracle["source"]


def test_distributions_for_import_dedupes_and_maps_absent_names_to_empty():
    import importlib.metadata

    script = _script()
    version = importlib.metadata.version("numpy")
    packages = {"numpy": ["numpy", "numpy"], "np_alias": ["numpy"]}
    assert script.distributions_for_import("numpy", packages) == {
        "numpy": version
    }
    assert script.distributions_for_import("absent_module", packages) == {}
    environment = script._environment(
        ssa_parameters_revision="INVENTED", packages=packages
    )
    assert environment["packages"] == {"numpy": version}
    assert environment["distributions_by_import"]["populace_dynamics"] == []
