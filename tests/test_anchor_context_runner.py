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

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "run_anchor_context_report.py"
REGISTRATION = "registrations/fixture anchor context"


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
    scripts.mkdir(parents=True)
    estimates.mkdir(parents=True)
    (scripts / LAUNCHER.name).write_bytes(LAUNCHER.read_bytes())
    (repository / ".gitignore").write_text(
        "__pycache__/\n*.py[cod]\n*.so\n",
        encoding="utf-8",
    )
    (estimates.parent / "__init__.py").write_text("", encoding="utf-8")
    (estimates / "__init__.py").write_text("", encoding="utf-8")

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
            str(repository / "scripts" / LAUNCHER.name),
            "--registration",
            registration,
        ],
        cwd=repository,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


def _assert_refusal(
    completed: subprocess.CompletedProcess[str],
    *,
    reason_detail: str,
    import_marker: Path,
    sentinel: Path | None = None,
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
    assert completed.stderr.count("\n") == 1
    assert not import_marker.exists()
    if sentinel is not None:
        assert not any(sentinel.iterdir())


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

    _assert_refusal(
        completed,
        reason_detail=reason_detail,
        import_marker=import_marker,
        sentinel=sentinel,
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
            str(repository / "scripts" / LAUNCHER.name),
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

    _assert_refusal(
        completed,
        reason_detail=reason_detail,
        import_marker=import_marker,
    )


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
