"""Sealed, fixture-only rehearsal tests for the context report."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from populace_dynamics.estimates import anchor_context_registry as registry
from populace_dynamics.estimates import (
    anchor_context_rehearsal as rehearsal,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
SCRIPT = REPOSITORY_ROOT / "scripts/rehearse_anchor_context_report.py"
EXPECTED_SUCCESS = {
    "checks": [
        "fixed_fixture_identity_gate",
        "success_ceremony_and_validators",
        "canonical_sidecar_publication",
        "typed_incident_publication",
        "private_root_cleanup",
    ],
    "status": "passed",
}


def test_committed_manifest_is_exact_canonical_and_fixture_only():
    manifest, raw = rehearsal._load_committed_manifest(REPOSITORY_ROOT)

    assert manifest["fixture_only"] is True
    assert [row["role"] for row in manifest["inputs"]] == [
        "first_estimates",
        "anchor",
    ]
    assert rehearsal.publication.canonical_json_bytes(manifest) == raw


@pytest.mark.parametrize(
    ("role", "field", "production_value"),
    [
        (
            "first",
            "path",
            registry.FIRST_ESTIMATES_INPUT_PATH,
        ),
        (
            "first",
            "sha256",
            registry.FIRST_ESTIMATES_INPUT_SHA256,
        ),
        (
            "anchor",
            "path",
            registry.ANCHOR_INPUT_PATH,
        ),
        (
            "anchor",
            "sha256",
            registry.ANCHOR_INPUT_SHA256,
        ),
        (
            "anchor",
            "artifact_vintage_id",
            registry.ANCHOR_ARTIFACT_VINTAGE_ID,
        ),
        (
            "first",
            "path",
            "tests/fixtures/anchor_context/unregistered_fixture.json",
        ),
    ],
)
def test_production_or_unregistered_identity_is_refused_before_input_read(
    role: str,
    field: str,
    production_value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    first, anchor = rehearsal._fixed_fixture_identities()
    mutant_first = copy.deepcopy(first)
    mutant_anchor = copy.deepcopy(anchor)
    target = mutant_first if role == "first" else mutant_anchor
    target[field] = production_value
    attempted_read = False

    def forbidden_read(*_args, **_kwargs):
        nonlocal attempted_read
        attempted_read = True
        raise AssertionError("identity gate attempted an input read")

    monkeypatch.setattr(rehearsal.os, "read", forbidden_read)
    with pytest.raises(ValueError):
        rehearsal._populate_private_root(
            source_root=REPOSITORY_ROOT,
            private_root=tmp_path / "private",
            manifest_bytes=b"fixture manifest is not reached",
            first_estimates_input=mutant_first,
            anchor_input=mutant_anchor,
        )
    assert attempted_read is False


@pytest.mark.parametrize("symlink_kind", ["fixture", "parent"])
def test_fixture_source_symlink_is_refused_before_input_read(
    symlink_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source_root = (tmp_path / "source").resolve()
    fixture_path = Path(rehearsal._FIRST_FIXTURE_PATH)
    source = source_root / fixture_path
    outside = (tmp_path / "outside").resolve()
    outside.mkdir()
    if symlink_kind == "fixture":
        source.parent.mkdir(parents=True)
        target = outside / source.name
        target.write_bytes(b"not read")
        source.symlink_to(target)
    else:
        source.parent.parent.mkdir(parents=True)
        target_parent = outside / source.parent.name
        target_parent.mkdir()
        (target_parent / source.name).write_bytes(b"not read")
        source.parent.symlink_to(target_parent)

    attempted_read = False

    def forbidden_read(*_args, **_kwargs):
        nonlocal attempted_read
        attempted_read = True
        raise AssertionError("symlink gate attempted an input read")

    monkeypatch.setattr(rehearsal.os, "read", forbidden_read)
    first, anchor = rehearsal._fixed_fixture_identities()
    with pytest.raises(
        rehearsal.FixtureRehearsalError,
        match="symlink",
    ):
        rehearsal._populate_private_root(
            source_root=source_root,
            private_root=tmp_path / "private",
            manifest_bytes=b"fixture manifest is not reached",
            first_estimates_input=first,
            anchor_input=anchor,
        )
    assert attempted_read is False


@pytest.mark.parametrize("symlink_kind", ["manifest", "parent"])
def test_manifest_symlink_is_refused_before_read(
    symlink_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source_root = (tmp_path / "source").resolve()
    manifest = source_root / rehearsal._MANIFEST_PATH
    outside = (tmp_path / "outside").resolve()
    outside.mkdir()
    if symlink_kind == "manifest":
        manifest.parent.mkdir(parents=True)
        target = outside / manifest.name
        target.write_bytes(b"not read")
        manifest.symlink_to(target)
    else:
        manifest.parent.parent.mkdir(parents=True)
        target_parent = outside / manifest.parent.name
        target_parent.mkdir()
        (target_parent / manifest.name).write_bytes(b"not read")
        manifest.parent.symlink_to(target_parent)

    attempted_read = False

    def forbidden_read(*_args, **_kwargs):
        nonlocal attempted_read
        attempted_read = True
        raise AssertionError("manifest symlink gate attempted a read")

    monkeypatch.setattr(rehearsal.os, "read", forbidden_read)
    with pytest.raises(
        rehearsal.FixtureRehearsalError,
        match="symlink",
    ):
        rehearsal._load_committed_manifest(source_root)
    assert attempted_read is False


@pytest.mark.parametrize(
    "protected_relative",
    [
        registry.FIRST_ESTIMATES_INPUT_PATH,
        registry.ANCHOR_INPUT_PATH,
    ],
)
def test_fixed_source_reader_rejects_direct_production_path_before_read(
    protected_relative: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source_root = (tmp_path / "source").resolve()
    source_root.mkdir()
    reads = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal reads
        reads += 1
        raise AssertionError("production input bytes were read")

    monkeypatch.setattr(rehearsal.os, "read", forbidden_read)

    with pytest.raises(
        rehearsal.FixtureRehearsalError,
        match="not fixed",
    ):
        rehearsal._read_sealed_fixture_source(
            source_root,
            protected_relative,
        )

    assert reads == 0


@pytest.mark.parametrize(
    ("fixture_relative", "protected_relative"),
    [
        (
            rehearsal._FIRST_FIXTURE_PATH,
            registry.FIRST_ESTIMATES_INPUT_PATH,
        ),
        (
            rehearsal._ANCHOR_FIXTURE_PATH,
            registry.ANCHOR_INPUT_PATH,
        ),
        (
            rehearsal._MANIFEST_PATH.as_posix(),
            registry.FIRST_ESTIMATES_INPUT_PATH,
        ),
    ],
)
def test_fixed_source_reader_rejects_production_hardlink_before_read(
    fixture_relative: str,
    protected_relative: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source_root = (tmp_path / "source").resolve()
    protected = source_root / protected_relative
    protected.parent.mkdir(parents=True)
    protected.write_bytes(b"protected production bytes")
    fixture = source_root / fixture_relative
    fixture.parent.mkdir(parents=True, exist_ok=True)
    os.link(protected, fixture)
    reads = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal reads
        reads += 1
        raise AssertionError("hardlinked production bytes were read")

    monkeypatch.setattr(rehearsal.os, "read", forbidden_read)

    with pytest.raises(
        rehearsal.FixtureRehearsalError,
        match="singly linked|aliases a production input",
    ):
        rehearsal._read_sealed_fixture_source(
            source_root,
            fixture_relative,
        )

    assert reads == 0


@pytest.mark.parametrize(
    ("fixture_relative", "protected_relative"),
    [
        (
            rehearsal._FIRST_FIXTURE_PATH,
            registry.FIRST_ESTIMATES_INPUT_PATH,
        ),
        (
            rehearsal._ANCHOR_FIXTURE_PATH,
            registry.ANCHOR_INPUT_PATH,
        ),
        (
            rehearsal._MANIFEST_PATH.as_posix(),
            registry.FIRST_ESTIMATES_INPUT_PATH,
        ),
    ],
)
def test_fixed_source_reader_rejects_reverse_production_symlink_before_read(
    fixture_relative: str,
    protected_relative: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source_root = (tmp_path / "source").resolve()
    fixture = source_root / fixture_relative
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"fixture bytes that must not be read")
    protected = source_root / protected_relative
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.symlink_to(fixture)
    reads = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal reads
        reads += 1
        raise AssertionError("reverse-aliased production bytes were read")

    monkeypatch.setattr(rehearsal.os, "read", forbidden_read)

    with pytest.raises(
        rehearsal.FixtureRehearsalError,
        match="production input path contains a symlink",
    ):
        rehearsal._read_sealed_fixture_source(
            source_root,
            fixture_relative,
        )

    assert reads == 0


def test_fixed_source_reader_rejects_oversize_file_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source_root = (tmp_path / "source").resolve()
    fixture = source_root / rehearsal._FIRST_FIXTURE_PATH
    fixture.parent.mkdir(parents=True)
    with fixture.open("wb") as stream:
        stream.truncate(rehearsal._SOURCE_MAX_BYTES + 1)
    reads = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal reads
        reads += 1
        raise AssertionError("oversize fixture bytes were read")

    monkeypatch.setattr(rehearsal.os, "read", forbidden_read)

    with pytest.raises(
        rehearsal.FixtureRehearsalError,
        match="exceeds byte bound",
    ):
        rehearsal._read_sealed_fixture_source(
            source_root,
            rehearsal._FIRST_FIXTURE_PATH,
        )

    assert reads == 0


def _sealed_command(sentinel: Path) -> list[str]:
    return [
        sys.executable,
        "-I",
        "-B",
        "-X",
        f"pycache_prefix={sentinel}",
        str(SCRIPT),
    ]


def _production_output_state() -> tuple[bool, bool]:
    return tuple(
        os.path.lexists(REPOSITORY_ROOT / relative)
        for relative in (
            registry.PRIMARY_OUTPUT_PATH,
            registry.SIDECAR_OUTPUT_PATH,
        )
    )


def test_sealed_subprocess_rehearses_success_and_typed_incident(
    tmp_path: Path,
):
    sentinel = tmp_path / "fresh-empty-pycache"
    sentinel.mkdir()
    before = _production_output_state()

    completed = subprocess.run(
        _sealed_command(sentinel),
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert (
        completed.returncode == 0
    ), f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == EXPECTED_SUCCESS
    assert not any(sentinel.iterdir())
    assert _production_output_state() == before


@pytest.mark.parametrize("sealed", [False, True])
def test_cli_refuses_unsealed_or_argument_bearing_invocation(
    sealed: bool,
    tmp_path: Path,
):
    if sealed:
        sentinel = tmp_path / "fresh-empty-pycache"
        sentinel.mkdir()
        command = [*_sealed_command(sentinel), "unexpected-input-path"]
    else:
        command = [sys.executable, str(SCRIPT)]

    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert json.loads(completed.stderr) == {
        "reason": "unsealed_or_noncanonical_invocation",
        "status": "refused",
    }
