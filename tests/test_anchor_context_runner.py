"""Reader-free tests for the sealed anchor-context report launcher."""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from populace_dynamics.estimates import (
    anchor_context_publication as publication,
)

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "run_anchor_context_report.py"
REGISTRATION = "docs/registrations/fixture_anchor_context.json"
REGISTRATION_REFERENCE = "anchor-context-runner-fixture"


def _load_launcher():
    spec = importlib.util.spec_from_file_location(
        "_test_run_anchor_context_report",
        LAUNCHER,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
    )


def _guard_repository(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    repository = tmp_path / "repo"
    scripts = repository / "scripts"
    estimates = repository / "src/populace_dynamics/estimates"
    registrations = repository / "docs/registrations"
    runs = repository / "runs"
    scripts.mkdir(parents=True)
    estimates.mkdir(parents=True)
    registrations.mkdir(parents=True)
    runs.mkdir(parents=True)
    (scripts / LAUNCHER.name).write_bytes(LAUNCHER.read_bytes())
    (repository / ".gitignore").write_text(
        (
            "__pycache__/\n"
            "*.py[cod]\n"
            "*.so\n"
            "runs/anchor_context_report_incident_*.json\n"
        ),
        encoding="utf-8",
    )
    (runs / ".gitkeep").write_bytes(b"")
    (estimates.parent / "__init__.py").write_text("", encoding="utf-8")
    (estimates / "__init__.py").write_text("", encoding="utf-8")
    configuration = publication.registered_configuration_echo(
        registration_reference=REGISTRATION_REFERENCE,
        implementation_commit="c" * 40,
        invocation=["fixture anchor-context launcher invocation"],
    )
    (repository / REGISTRATION).write_bytes(
        publication.canonical_json_bytes(configuration)
    )

    import_marker = tmp_path / "coordinator-imported"
    call_marker = tmp_path / "coordinator-call"
    published_path = tmp_path / "published-artifact"
    (estimates / "anchor_context_coordinator.py").write_text(
        "\n".join(
            (
                "from pathlib import Path",
                "from types import SimpleNamespace",
                f"Path({str(import_marker)!r}).write_text("
                "'imported\\n', encoding='utf-8')",
                "",
                "def run_registered_anchor_context(registration_path):",
                f"    Path({str(call_marker)!r}).write_text(",
                "        str(registration_path), encoding='utf-8'",
                "    )",
                "    return SimpleNamespace(",
                "        status='published',",
                f"        path=Path({str(published_path)!r}),",
                "        phase='publication',",
                "        reason=None,",
                "    )",
                "",
            )
        ),
        encoding="utf-8",
    )
    _git(repository, "init", "--quiet")
    _git(repository, "add", ".")
    _git(
        repository,
        "-c",
        "user.name=Anchor Context Runner Test",
        "-c",
        "user.email=anchor-context@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "sealed runner fixture",
    )
    return repository, import_marker, call_marker, published_path


def _sealed_run(
    repository: Path,
    sentinel: Path,
    *,
    registration: str = REGISTRATION,
) -> subprocess.CompletedProcess[str]:
    sentinel.mkdir()
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            f"pycache_prefix={sentinel}",
            f"scripts/{LAUNCHER.name}",
            "--registration",
            registration,
        ],
        cwd=repository,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


def _assert_incident(
    completed: subprocess.CompletedProcess[str],
    *,
    repository: Path,
    reason_detail: str,
    import_marker: Path,
    sentinel: Path | None = None,
    expected_index: int = 1,
    expected_reason: str = "preparation_pre_import_guard_refused",
    coordinator_imported: bool = False,
) -> None:
    assert completed.returncode == 1
    assert completed.stderr == ""
    relative = f"runs/anchor_context_report_incident_{expected_index}.json"
    path = repository / relative
    assert json.loads(completed.stdout) == {
        "path": path.as_posix(),
        "phase": "preparation",
        "reason": expected_reason,
        "status": "incident",
    }
    assert completed.stdout.count("\n") == 1
    payload = path.read_bytes()
    record = json.loads(payload)
    assert payload == publication.canonical_json_bytes(record)
    assert set(record) == {
        "schema_version",
        "incident_index",
        "timestamp_utc",
        "phase",
        "reason",
        "reason_detail",
        "registration_reference",
        "configuration_echo",
        "artifact_path",
    }
    assert record["schema_version"] == "anchor_context_report_incident.v1"
    assert record["incident_index"] == expected_index
    assert record["phase"] == "preparation"
    assert record["reason"] == expected_reason
    assert record["reason_detail"] == reason_detail
    assert record["registration_reference"] == REGISTRATION_REFERENCE
    assert record["configuration_echo"] == json.loads(
        (repository / REGISTRATION).read_bytes()
    )
    assert record["artifact_path"] is None
    publication.validate_anchor_context_incident(
        path=path,
        expected_configuration_echo=record["configuration_echo"],
        repository_root=repository,
    )
    assert import_marker.exists() is coordinator_imported
    if sentinel is not None:
        assert not any(sentinel.iterdir())


def _assert_procedural_refusal(
    completed: subprocess.CompletedProcess[str],
    *,
    reason_detail: str,
    import_marker: Path,
) -> None:
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert json.loads(completed.stderr) == {
        "path": None,
        "phase": "preparation",
        "reason": "preparation_pre_import_guard_refused",
        "reason_detail": reason_detail,
        "status": "procedural_refusal",
    }
    assert not import_marker.exists()


def test_canonical_sealed_invocation_passes_clean_pre_import_guard(
    tmp_path,
):
    repository, import_marker, call_marker, published_path = _guard_repository(
        tmp_path
    )
    sentinel = tmp_path / "fresh-empty-pycache"

    completed = _sealed_run(repository, sentinel)

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "path": published_path.as_posix(),
        "phase": "publication",
        "reason": None,
        "status": "published",
    }
    assert completed.stdout.count("\n") == 1
    assert import_marker.read_text(encoding="utf-8") == "imported\n"
    assert call_marker.read_text(encoding="utf-8") == REGISTRATION
    assert not any(sentinel.iterdir())


def test_clean_committed_coordinator_import_failure_publishes_incident(
    tmp_path,
):
    repository, import_marker, call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    coordinator_path = (
        repository
        / "src/populace_dynamics/estimates/anchor_context_coordinator.py"
    )
    coordinator_path.write_text(
        "\n".join(
            (
                "from pathlib import Path",
                f"Path({str(import_marker)!r}).write_text(",
                "    'import attempted\\n', encoding='utf-8'",
                ")",
                "raise RuntimeError('committed coordinator import failed')",
                "",
            )
        ),
        encoding="utf-8",
    )
    _git(
        repository, "add", coordinator_path.relative_to(repository).as_posix()
    )
    _git(
        repository,
        "-c",
        "user.name=Anchor Context Runner Test",
        "-c",
        "user.email=anchor-context@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "commit failing coordinator fixture",
    )
    sentinel = tmp_path / "import-failure-sentinel"

    completed = _sealed_run(repository, sentinel)

    _assert_incident(
        completed,
        repository=repository,
        reason_detail="committed coordinator import failed",
        import_marker=import_marker,
        sentinel=sentinel,
        expected_reason="preparation_coordinator_entry_failed",
        coordinator_imported=True,
    )
    assert import_marker.read_text(encoding="utf-8") == "import attempted\n"
    assert not call_marker.exists()
    assert (
        len(
            list(
                (repository / "runs").glob(
                    "anchor_context_report_incident_*.json"
                )
            )
        )
        == 1
    )


def test_coordinator_exception_after_incident_does_not_publish_second(
    tmp_path,
):
    repository, import_marker, _call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    coordinator_path = (
        repository
        / "src/populace_dynamics/estimates/anchor_context_coordinator.py"
    )
    coordinator_path.write_text(
        "\n".join(
            (
                "import json",
                "from pathlib import Path",
                f"Path({str(import_marker)!r}).write_text(",
                "    'imported\\n', encoding='utf-8'",
                ")",
                "",
                "def run_registered_anchor_context(registration_path):",
                "    root = Path(__file__).resolve().parents[3]",
                "    configuration = json.loads(",
                "        (root / registration_path).read_bytes()",
                "    )",
                "    record = {",
                "        'schema_version': "
                "'anchor_context_report_incident.v1',",
                "        'incident_index': 1,",
                "        'timestamp_utc': '2026-07-27T12:00:00Z',",
                "        'phase': 'compute',",
                "        'reason': 'external_fixture_failure',",
                "        'reason_detail': 'published before raise',",
                "        'registration_reference': "
                "configuration['registration_reference'],",
                "        'configuration_echo': configuration,",
                "        'artifact_path': None,",
                "    }",
                "    payload = (json.dumps(",
                "        record, sort_keys=True, separators=(',', ':'),",
                "        ensure_ascii=True, allow_nan=False",
                "    ) + '\\n').encode('utf-8')",
                "    (root / 'runs/anchor_context_report_incident_1.json')"
                ".write_bytes(payload)",
                "    raise RuntimeError('raised after publishing incident')",
                "",
            )
        ),
        encoding="utf-8",
    )
    _git(
        repository, "add", coordinator_path.relative_to(repository).as_posix()
    )
    _git(
        repository,
        "-c",
        "user.name=Anchor Context Runner Test",
        "-c",
        "user.email=anchor-context@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "commit incident then raise fixture",
    )
    sentinel = tmp_path / "incident-before-raise-sentinel"

    completed = _sealed_run(repository, sentinel)

    incident = repository / "runs/anchor_context_report_incident_1.json"
    assert completed.returncode == 1
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "path": incident.as_posix(),
        "phase": "compute",
        "reason": "external_fixture_failure",
        "status": "incident",
    }
    assert [
        path.name
        for path in (repository / "runs").glob(
            "anchor_context_report_incident_*.json"
        )
    ] == [incident.name]
    publication.validate_anchor_context_incident(
        path=incident,
        expected_configuration_echo=json.loads(
            (repository / REGISTRATION).read_bytes()
        ),
        repository_root=repository,
    )
    assert import_marker.read_text(encoding="utf-8") == "imported\n"
    assert not any(sentinel.iterdir())


@pytest.mark.parametrize(
    ("checkout_state", "reason_detail"),
    [
        (
            "dirty",
            "launcher requires an entirely clean checkout",
        ),
        (
            "assume-unchanged",
            "tracked files use assume-unchanged or skip-worktree flags",
        ),
        (
            "skip-worktree",
            "tracked files use assume-unchanged or skip-worktree flags",
        ),
        (
            "ignored-executable",
            "code roots contain ignored executable artifacts",
        ),
    ],
)
def test_pre_import_guard_refuses_unsealed_checkout_before_coordinator_import(
    tmp_path,
    checkout_state,
    reason_detail,
):
    repository, import_marker, _call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    coordinator_path = (
        repository
        / "src/populace_dynamics/estimates/anchor_context_coordinator.py"
    )
    if checkout_state == "dirty":
        coordinator_path.write_text(
            "raise RuntimeError('dirty coordinator imported')\n",
            encoding="utf-8",
        )
    elif checkout_state in {"assume-unchanged", "skip-worktree"}:
        option = (
            "--assume-unchanged"
            if checkout_state == "assume-unchanged"
            else "--skip-worktree"
        )
        relative = coordinator_path.relative_to(repository).as_posix()
        _git(repository, "update-index", option, "--", relative)
        coordinator_path.write_text(
            "raise RuntimeError('hidden coordinator imported')\n",
            encoding="utf-8",
        )
        assert (
            _git(
                repository,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ).stdout
            == b""
        )
    else:
        ignored = (
            repository
            / "src/populace_dynamics/estimates/__pycache__/shadow.pyc"
        )
        ignored.parent.mkdir()
        ignored.write_bytes(b"ignored executable fixture\n")
        assert (
            _git(
                repository,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ).stdout
            == b""
        )

    sentinel = tmp_path / "refusal-pycache"
    completed = _sealed_run(repository, sentinel)

    _assert_incident(
        completed,
        repository=repository,
        reason_detail=reason_detail,
        import_marker=import_marker,
        sentinel=sentinel,
    )


def test_git_guard_failure_uses_lawful_descriptor_registration_echo(
    tmp_path,
):
    repository, import_marker, _call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    (repository / ".git").rename(repository / "corrupt-git-directory")
    sentinel = tmp_path / "git-failure-sentinel"

    completed = _sealed_run(repository, sentinel)

    _assert_incident(
        completed,
        repository=repository,
        reason_detail="Git could not verify the pre-import report checkout",
        import_marker=import_marker,
        sentinel=sentinel,
    )


def test_git_fallback_does_not_accept_mismatched_committed_bytes(tmp_path):
    repository, _import_marker, _call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    launcher = _load_launcher()
    registration = repository / REGISTRATION
    configuration = json.loads(registration.read_bytes())
    configuration["registration_reference"] = "changed-after-commit"
    registration.write_bytes(publication.canonical_json_bytes(configuration))

    with pytest.raises(
        ValueError,
        match="registration bytes differ from the committed record",
    ):
        launcher._publish_pre_import_incident(
            repository,
            registration,
            launcher._GitVerificationUnavailable("guard Git failed"),
            permit_unavailable_git=True,
        )

    assert not list(
        (repository / "runs").glob("anchor_context_report_incident_*.json")
    )


@pytest.mark.parametrize(
    ("sealed", "populate_sentinel", "reason_detail"),
    [
        (
            False,
            False,
            "runner requires python -I -B -X pycache_prefix=<fresh empty dir>",
        ),
        (
            True,
            True,
            "pycache prefix is not a fresh empty directory",
        ),
    ],
)
def test_launcher_refuses_noncanonical_interpreter_before_coordinator_import(
    tmp_path,
    sealed,
    populate_sentinel,
    reason_detail,
):
    repository, import_marker, _call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    sentinel = tmp_path / "pycache-sentinel"
    sentinel.mkdir()
    if populate_sentinel:
        (sentinel / "not-empty").write_text("occupied\n", encoding="utf-8")
    command = [sys.executable]
    if sealed:
        command.extend(
            [
                "-I",
                "-B",
                "-X",
                f"pycache_prefix={sentinel}",
            ]
        )
    command.extend(
        [
            f"scripts/{LAUNCHER.name}",
            "--registration",
            REGISTRATION,
        ]
    )

    completed = subprocess.run(
        command,
        cwd=repository,
        capture_output=True,
        text=True,
    )

    _assert_incident(
        completed,
        repository=repository,
        reason_detail=reason_detail,
        import_marker=import_marker,
    )


def test_pre_import_incidents_append_contiguously_without_overwrite(tmp_path):
    repository, import_marker, _call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    coordinator_path = (
        repository
        / "src/populace_dynamics/estimates/anchor_context_coordinator.py"
    )
    coordinator_path.write_text(
        "raise RuntimeError('dirty coordinator imported')\n",
        encoding="utf-8",
    )
    first = _sealed_run(repository, tmp_path / "first-sentinel")
    first_path = repository / "runs/anchor_context_report_incident_1.json"
    first_bytes = first_path.read_bytes()
    second = _sealed_run(repository, tmp_path / "second-sentinel")

    _assert_incident(
        first,
        repository=repository,
        reason_detail="launcher requires an entirely clean checkout",
        import_marker=import_marker,
        expected_index=1,
    )
    _assert_incident(
        second,
        repository=repository,
        reason_detail="launcher requires an entirely clean checkout",
        import_marker=import_marker,
        expected_index=2,
    )
    assert first_path.read_bytes() == first_bytes


@pytest.mark.parametrize(
    "filename",
    [
        "anchor_context_report_incident_0.json",
        "anchor_context_report_incident_01.json",
        "anchor_context_report_incident_1",
        "anchor_context_report_incident_1.json.tmp",
        "anchor_context_report_incident_invalid.json",
    ],
)
def test_next_incident_index_rejects_malformed_prefixed_name(
    tmp_path,
    filename,
):
    launcher = _load_launcher()
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / filename).write_bytes(b"malformed incident fixture\n")
    descriptor = os.open(runs, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        with pytest.raises(
            ValueError,
            match="existing incident filename is malformed",
        ):
            launcher._next_incident_index(descriptor)
    finally:
        os.close(descriptor)


@pytest.mark.parametrize(
    "registration",
    [
        "runs/first_estimates_v1.json",
        (
            "data/external/"
            "ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
        ),
    ],
)
def test_pre_import_refusal_rejects_production_input_as_registration(
    tmp_path,
    registration,
):
    repository, import_marker, _call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    coordinator_path = (
        repository
        / "src/populace_dynamics/estimates/anchor_context_coordinator.py"
    )
    coordinator_path.write_text(
        "raise RuntimeError('dirty coordinator imported')\n",
        encoding="utf-8",
    )

    completed = _sealed_run(
        repository,
        tmp_path / "protected-path-sentinel",
        registration=registration,
    )

    _assert_procedural_refusal(
        completed,
        reason_detail="launcher requires an entirely clean checkout",
        import_marker=import_marker,
    )
    assert not list(
        (repository / "runs").glob("anchor_context_report_incident_*.json")
    )


@pytest.mark.parametrize(
    "alias_kind",
    ["hardlink", "reverse_hardlink", "symlink", "reverse_symlink"],
)
def test_bootstrap_registration_gate_rejects_production_alias_before_read(
    tmp_path,
    monkeypatch,
    alias_kind,
):
    repository, _import_marker, _call_marker, _published_path = (
        _guard_repository(tmp_path)
    )
    launcher = _load_launcher()
    registration = repository / REGISTRATION
    protected = repository / "runs/first_estimates_v1.json"
    original_registration = registration.read_bytes()
    if alias_kind == "hardlink":
        protected.write_bytes(b"protected production bytes")
        registration.unlink()
        os.link(protected, registration)
    elif alias_kind == "reverse_hardlink":
        os.link(registration, protected)
    elif alias_kind == "symlink":
        protected.write_bytes(b"protected production bytes")
        registration.unlink()
        registration.symlink_to(protected)
    else:
        protected.symlink_to(registration)
    read_attempts = 0
    leaf_open_attempts = 0
    successful_leaf_opens = 0
    real_open = launcher.os.open

    def forbidden_read(*_args, **_kwargs):
        nonlocal read_attempts
        read_attempts += 1
        raise AssertionError("protected production bytes were read")

    def monitored_open(path, *args, **kwargs):
        nonlocal leaf_open_attempts, successful_leaf_opens
        is_registration_leaf = (
            os.fspath(path) == registration.name
            and kwargs.get("dir_fd") is not None
        )
        if is_registration_leaf:
            leaf_open_attempts += 1
        descriptor = real_open(path, *args, **kwargs)
        if is_registration_leaf:
            successful_leaf_opens += 1
        return descriptor

    monkeypatch.setattr(launcher.os, "read", forbidden_read)
    monkeypatch.setattr(launcher.os, "open", monitored_open)

    with pytest.raises((OSError, ValueError)):
        launcher._read_registered_configuration(repository, registration)

    assert read_attempts == 0
    assert leaf_open_attempts == 0
    assert successful_leaf_opens == 0
    if alias_kind == "reverse_symlink":
        assert registration.read_bytes() == original_registration


@pytest.mark.parametrize(
    ("status", "reason", "expected_exit"),
    [
        ("published", None, 0),
        ("incident", "fixture_publication_failure", 1),
    ],
)
def test_main_forwards_only_raw_registration_and_prints_result(
    tmp_path,
    monkeypatch,
    capsys,
    status,
    reason,
    expected_exit,
):
    launcher = _load_launcher()
    raw_registration = "not-opened registration fixture"
    result_path = tmp_path / "coordinator-result"
    calls: list[tuple] = []
    events: list[str] = []
    monkeypatch.setattr(
        launcher,
        "_arguments",
        lambda: SimpleNamespace(registration=raw_registration),
    )
    monkeypatch.setattr(
        launcher,
        "_assert_pre_import_guard",
        lambda repository: events.append(f"guard:{repository.name}"),
    )

    def run(*arguments):
        events.append("coordinator")
        calls.append(arguments)
        return SimpleNamespace(
            status=status,
            path=result_path,
            phase="publication",
            reason=reason,
        )

    monkeypatch.setattr(launcher, "_run_coordinator", run)

    assert launcher.main() == expected_exit
    assert events == [f"guard:{ROOT.name}", "coordinator"]
    assert calls == [(raw_registration,)]
    assert not (tmp_path / raw_registration).exists()
    assert json.loads(capsys.readouterr().out) == {
        "path": result_path.as_posix(),
        "phase": "publication",
        "reason": reason,
        "status": status,
    }


@pytest.mark.parametrize(
    "injected_arguments",
    [
        ["--repository-root", "/tmp/injected"],
        ["--first-estimates-input", "/tmp/injected"],
        ["--anchor-input", "/tmp/injected"],
        ["--output", "/tmp/injected"],
    ],
)
def test_cli_has_no_input_output_or_repository_injection(
    monkeypatch,
    capsys,
    injected_arguments,
):
    launcher = _load_launcher()
    assert list(inspect.signature(launcher._run_coordinator).parameters) == [
        "registration"
    ]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            LAUNCHER.name,
            "--registration",
            REGISTRATION,
            *injected_arguments,
        ],
    )

    with pytest.raises(SystemExit) as error:
        launcher._arguments()

    assert error.value.code == 2
    assert "unrecognized arguments:" in capsys.readouterr().err
