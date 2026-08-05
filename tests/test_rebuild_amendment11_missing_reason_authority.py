"""Fresh raw-source reproduction gate for Amendment 11."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import rebuild_amendment11_missing_reason_authority as builder

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()
SCRIPT = (
    REPOSITORY_ROOT / "scripts/rebuild_amendment11_missing_reason_authority.py"
)
ARTIFACT = (
    REPOSITORY_ROOT
    / "data/external/psid_missing_reason_code_authority_v1.json"
)

pytestmark = pytest.mark.skipif(
    not PSID_ROOT.exists(), reason="registered PSID corpus is unavailable"
)


def test_fresh_47_source_build_is_byte_equal_to_committed_authority():
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--check",
            "--output",
            str(ARTIFACT),
            "--psid-root",
            str(PSID_ROOT),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    summary = json.loads(completed.stdout)
    assert completed.stderr == ""
    assert summary["status"] == "pass"
    assert summary["check"] is True
    assert summary["source_member_count"] == 561_873
    assert summary["literal_member_count"] == 524_590
    assert summary["lexical_missing_candidate_count"] == 231_263
    assert summary["authorized_reason_assignment_count"] == 0
    assert summary["byte_size"] == ARTIFACT.stat().st_size


@pytest.mark.parametrize("mutation", ["one_byte", "truncate"])
def test_raw_source_mutation_aborts_before_emission(tmp_path, mutation):
    relative = Path("family/1968/fam1968_codebook.pdf")
    source = PSID_ROOT / relative
    target = tmp_path / "psid" / relative
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    if mutation == "one_byte":
        with target.open("r+b") as stream:
            original = stream.read(1)
            stream.seek(0)
            stream.write(bytes((original[0] ^ 1,)))
    else:
        with target.open("r+b") as stream:
            stream.truncate(source.stat().st_size - 1)
    output = tmp_path / "must-not-exist.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output",
            str(output),
            "--psid-root",
            str(tmp_path / "psid"),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert not output.exists()
    expected = (
        "SHA-256 mismatch" if mutation == "one_byte" else "byte-size mismatch"
    )
    assert expected in completed.stderr


def _run_with_output(output):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output",
            str(output),
            "--psid-root",
            str(PSID_ROOT),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )


def test_output_cannot_alias_a_registered_source():
    source = PSID_ROOT / "family/1968/fam1968_codebook.pdf"
    before = source.read_bytes()
    completed = _run_with_output(source)
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "aliases the PSID source tree" in completed.stderr
    assert source.read_bytes() == before


def test_symbolic_link_output_is_rejected_without_touching_target(tmp_path):
    target = tmp_path / "target.json"
    target.write_bytes(b"sentinel")
    output = tmp_path / "output.json"
    output.symlink_to(target)
    completed = _run_with_output(output)
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "symbolic link" in completed.stderr
    assert target.read_bytes() == b"sentinel"


def test_hard_link_output_is_rejected_without_touching_target(tmp_path):
    target = tmp_path / "target.json"
    target.write_bytes(b"sentinel")
    output = tmp_path / "output.json"
    os.link(target, output)
    completed = _run_with_output(output)
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "hard-link aliases" in completed.stderr
    assert target.read_bytes() == b"sentinel"


def test_hard_link_added_during_descriptor_read_is_rejected(
    tmp_path, monkeypatch
):
    fake_source_root = tmp_path / "fake-psid"
    fake_source_root.mkdir()
    output = tmp_path / "output.json"
    output.write_bytes(b"sentinel")
    target = builder.validate_output_target(output, fake_source_root)
    original_fstat = builder.os.fstat
    regular_calls = 0

    def inject_link_count(descriptor):
        nonlocal regular_calls
        status = original_fstat(descriptor)
        if builder.stat_module.S_ISREG(status.st_mode):
            regular_calls += 1
            if regular_calls == 2:
                values = list(status)
                values[3] = 2
                return os.stat_result(values)
        return status

    monkeypatch.setattr(builder.os, "fstat", inject_link_count)
    try:
        with pytest.raises(builder.BuildError, match="gained hard-link"):
            builder._read_regular_leaf(
                target, target.name, require_single_link=True
            )
    finally:
        target.close()


def _committed_artifact_value():
    return json.loads(ARTIFACT.read_bytes())


def test_parent_swap_during_build_aborts_without_redirecting_output(
    tmp_path, monkeypatch
):
    parent = tmp_path / "output-parent"
    parent.mkdir()
    output = parent / "authority.json"
    output.write_bytes(b"prior accepted target")
    held_parent = tmp_path / "held-parent"
    fake_source_root = tmp_path / "fake-psid"
    fake_source_root.mkdir()

    def swap_parent(_registry_path, _psid_root):
        parent.rename(held_parent)
        parent.symlink_to(fake_source_root, target_is_directory=True)
        return _committed_artifact_value()

    monkeypatch.setattr(builder, "fresh_build", swap_parent)
    with pytest.raises(builder.BuildError, match="parent changed"):
        builder.main(
            [
                "--output",
                str(output),
                "--psid-root",
                str(fake_source_root),
            ]
        )

    assert (held_parent / output.name).read_bytes() == b"prior accepted target"
    assert not (fake_source_root / output.name).exists()


def test_containment_check_survives_parent_rename_race(tmp_path):
    source_root = tmp_path / "psid"
    parent = source_root / "output-parent"
    parent.mkdir(parents=True)
    held_parent = tmp_path / "held-parent"
    source_descriptor = builder._open_stable_directory(
        source_root.resolve(), "test source root"
    )
    parent_descriptor = builder._open_stable_directory(
        parent.resolve(), "test output parent"
    )
    resolved_source = source_root.resolve()
    resolved_parent = parent.resolve()
    try:
        parent.rename(held_parent)
        assert not builder._descriptor_is_within(
            source_descriptor, parent_descriptor
        )
        assert builder._path_is_within(resolved_source, resolved_parent)
    finally:
        os.close(parent_descriptor)
        os.close(source_descriptor)
        held_parent.rename(parent)


@pytest.mark.parametrize("replacement_kind", ["symlink", "hardlink"])
def test_check_rejects_leaf_alias_introduced_during_build(
    tmp_path, monkeypatch, replacement_kind
):
    fake_source_root = tmp_path / "fake-psid"
    fake_source_root.mkdir()
    source = fake_source_root / "candidate.json"
    source.write_bytes(ARTIFACT.read_bytes())
    output = tmp_path / "candidate.json"
    output.write_bytes(ARTIFACT.read_bytes())

    def swap_leaf(_registry_path, _psid_root):
        output.unlink()
        if replacement_kind == "symlink":
            output.symlink_to(source)
        else:
            os.link(source, output)
        return _committed_artifact_value()

    monkeypatch.setattr(builder, "fresh_build", swap_leaf)
    with pytest.raises(builder.BuildError):
        builder.main(
            [
                "--check",
                "--output",
                str(output),
                "--psid-root",
                str(fake_source_root),
            ]
        )
    assert source.read_bytes() == ARTIFACT.read_bytes()


@pytest.mark.parametrize("failure_effect", ["before", "after"])
def test_replacement_failure_restores_prior_target(
    tmp_path, monkeypatch, failure_effect
):
    fake_source_root = tmp_path / "fake-psid"
    fake_source_root.mkdir()
    output = tmp_path / "authority.json"
    prior = b"prior accepted target"
    output.write_bytes(prior)
    output.chmod(0o600)
    monkeypatch.setattr(
        builder,
        "fresh_build",
        lambda _registry_path, _psid_root: _committed_artifact_value(),
    )
    original_replace = builder.os.replace
    injected = False

    def fail_replacement(source, destination, *args, **kwargs):
        nonlocal injected
        if not injected and ".a11-stage-" in str(source):
            injected = True
            if failure_effect == "after":
                original_replace(source, destination, *args, **kwargs)
            raise OSError(f"injected {failure_effect}-effect failure")
        return original_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(builder.os, "replace", fail_replacement)
    with pytest.raises(builder.BuildError, match="prior target restored"):
        builder.main(
            [
                "--output",
                str(output),
                "--psid-root",
                str(fake_source_root),
            ]
        )
    assert injected
    assert output.read_bytes() == prior
    assert output.stat().st_mode & 0o777 == 0o600
    assert not tuple(tmp_path.glob(".authority.json.a11-*"))


def test_replacement_interrupt_restores_prior_target(tmp_path, monkeypatch):
    fake_source_root = tmp_path / "fake-psid"
    fake_source_root.mkdir()
    output = tmp_path / "authority.json"
    prior = b"prior accepted target"
    output.write_bytes(prior)
    monkeypatch.setattr(
        builder,
        "fresh_build",
        lambda _registry_path, _psid_root: _committed_artifact_value(),
    )
    original_replace = builder.os.replace
    injected = False

    def interrupt_after_replacement(source, destination, *args, **kwargs):
        nonlocal injected
        result = original_replace(source, destination, *args, **kwargs)
        if not injected and ".a11-stage-" in str(source):
            injected = True
            raise KeyboardInterrupt("injected after-effect interruption")
        return result

    monkeypatch.setattr(builder.os, "replace", interrupt_after_replacement)
    with pytest.raises(KeyboardInterrupt, match="after-effect interruption"):
        builder.main(
            [
                "--output",
                str(output),
                "--psid-root",
                str(fake_source_root),
            ]
        )
    assert injected
    assert output.read_bytes() == prior
    assert not tuple(tmp_path.glob(".authority.json.a11-*"))


@pytest.mark.parametrize("late_mutation", ["hardlink", "symlink"])
@pytest.mark.parametrize("directory_fsync_phase", [2, 3])
def test_post_replace_alias_mutation_aborts_and_restores_prior_target(
    tmp_path, monkeypatch, late_mutation, directory_fsync_phase
):
    fake_source_root = tmp_path / "fake-psid"
    fake_source_root.mkdir()
    output = tmp_path / "authority.json"
    prior = b"prior accepted target"
    output.write_bytes(prior)
    victim = tmp_path / "victim"
    victim.write_bytes(b"untouched victim")
    late_alias = tmp_path / "late-alias"
    monkeypatch.setattr(
        builder,
        "fresh_build",
        lambda _registry_path, _psid_root: _committed_artifact_value(),
    )
    original_fsync = builder.os.fsync
    injected = False
    directory_fsync_count = 0

    def mutate_on_post_replace_directory_fsync(descriptor):
        nonlocal directory_fsync_count, injected
        if os.path.isdir(f"/dev/fd/{descriptor}"):
            directory_fsync_count += 1
        if not injected and directory_fsync_count == directory_fsync_phase:
            injected = True
            if late_mutation == "hardlink":
                os.link(output, late_alias)
            else:
                output.unlink()
                output.symlink_to(victim)
        return original_fsync(descriptor)

    monkeypatch.setattr(
        builder.os, "fsync", mutate_on_post_replace_directory_fsync
    )
    with pytest.raises(builder.BuildError):
        builder.main(
            [
                "--output",
                str(output),
                "--psid-root",
                str(fake_source_root),
            ]
        )
    assert injected
    assert output.read_bytes() == prior
    assert victim.read_bytes() == b"untouched victim"
    assert not output.is_symlink()
    assert not tuple(tmp_path.glob(".authority.json.a11-*"))


def test_final_directory_fsync_failure_restores_prior_target(
    tmp_path, monkeypatch
):
    fake_source_root = tmp_path / "fake-psid"
    fake_source_root.mkdir()
    output = tmp_path / "authority.json"
    prior = b"prior accepted target"
    output.write_bytes(prior)
    monkeypatch.setattr(
        builder,
        "fresh_build",
        lambda _registry_path, _psid_root: _committed_artifact_value(),
    )
    original_fsync = builder.os.fsync
    directory_fsync_count = 0

    def fail_final_directory_fsync(descriptor):
        nonlocal directory_fsync_count
        if os.path.isdir(f"/dev/fd/{descriptor}"):
            directory_fsync_count += 1
            if directory_fsync_count == 3:
                raise OSError("injected final directory fsync failure")
        return original_fsync(descriptor)

    monkeypatch.setattr(builder.os, "fsync", fail_final_directory_fsync)
    with pytest.raises(builder.BuildError, match="prior target restored"):
        builder.main(
            [
                "--output",
                str(output),
                "--psid-root",
                str(fake_source_root),
            ]
        )
    assert directory_fsync_count >= 3
    assert output.read_bytes() == prior
    assert not tuple(tmp_path.glob(".authority.json.a11-*"))


def test_corrupted_backup_cannot_launder_rollback_bytes(tmp_path, monkeypatch):
    fake_source_root = tmp_path / "fake-psid"
    fake_source_root.mkdir()
    output = tmp_path / "authority.json"
    prior = b"prior accepted target"
    output.write_bytes(prior)
    monkeypatch.setattr(
        builder,
        "fresh_build",
        lambda _registry_path, _psid_root: _committed_artifact_value(),
    )
    original_replace = builder.os.replace
    injected = False

    def corrupt_backup_after_replacement(source, destination, *args, **kwargs):
        nonlocal injected
        result = original_replace(source, destination, *args, **kwargs)
        if not injected and ".a11-stage-" in str(source):
            injected = True
            backups = tuple(tmp_path.glob(".authority.json.a11-backup-*"))
            assert len(backups) == 1
            backups[0].write_bytes(b"CORRUPTED PREDECESSOR")
            raise OSError("injected after-effect replacement failure")
        return result

    monkeypatch.setattr(
        builder.os, "replace", corrupt_backup_after_replacement
    )
    with pytest.raises(builder.BuildError, match="prior target restored"):
        builder.main(
            [
                "--output",
                str(output),
                "--psid-root",
                str(fake_source_root),
            ]
        )
    assert injected
    assert output.read_bytes() == prior
    assert not tuple(tmp_path.glob(".authority.json.a11-*"))


def test_hidden_worker_cannot_overwrite_registered_source(tmp_path):
    source = PSID_ROOT / "family/1968/fam1968_codebook.pdf"
    before_sha256 = builder._sha256_file(source)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--worker-manifest",
            str(manifest),
            "--worker-output",
            str(source),
            "--worker-position",
            "0",
            "--worker-member-offset",
            "0",
            "--worker-capability",
            "a" * 64,
            "--psid-root",
            str(PSID_ROOT),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "worker output confinement" in completed.stderr
    assert builder._sha256_file(source) == before_sha256


def test_case_variant_registered_source_path_is_rejected_when_aliased():
    source = PSID_ROOT / "family/1968/fam1968_codebook.pdf"
    text = str(source)
    variant = Path(text.replace("/Users/", "/users/", 1))
    if not variant.exists() or not os.path.samefile(source, variant):
        pytest.skip("filesystem does not expose a case-variant alias")
    before_sha256 = builder._sha256_file(source)
    completed = _run_with_output(variant)
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "aliases the PSID source tree" in completed.stderr
    assert builder._sha256_file(source) == before_sha256


@pytest.mark.parametrize("mutation", ["same_size_content", "truncate"])
def test_registry_byte_mutation_aborts_before_source_access(
    tmp_path, monkeypatch, mutation
):
    monkeypatch.setattr(builder, "REPOSITORY_ROOT", tmp_path)
    registry = tmp_path / builder.EXPECTED_REGISTRY_PATH
    registry.parent.mkdir(parents=True)
    shutil.copyfile(REPOSITORY_ROOT / builder.EXPECTED_REGISTRY_PATH, registry)
    if mutation == "same_size_content":
        with registry.open("r+b") as stream:
            original = stream.read(1)
            stream.seek(0)
            stream.write(bytes((original[0] ^ 1,)))
        expected = "SHA-256"
    else:
        with registry.open("r+b") as stream:
            stream.truncate(builder.EXPECTED_REGISTRY_BYTE_SIZE - 1)
        expected = "byte-size"
    psid_root = tmp_path / "psid"
    psid_root.mkdir()
    source_hash_calls = 0

    def unexpected_source_hash(_path):
        nonlocal source_hash_calls
        source_hash_calls += 1
        return "0" * 64

    monkeypatch.setattr(builder, "_sha256_file", unexpected_source_hash)
    with pytest.raises(builder.BuildError, match=expected):
        builder.load_and_authenticate_sources(registry, psid_root)
    assert source_hash_calls == 0


@pytest.mark.parametrize(
    "raw",
    [
        b'{"duplicate":1,"duplicate":2}\n',
        b'{"nonfinite":NaN}\n',
        b"\xff",
    ],
)
def test_strict_registry_json_rejects_duplicate_nonfinite_and_non_utf8(raw):
    with pytest.raises(builder.BuildError):
        builder.strict_json_bytes(raw, "mutation fixture")


def test_last_registered_source_hash_failure_precedes_semantic_work(
    monkeypatch,
):
    registry = json.loads(
        (REPOSITORY_ROOT / builder.EXPECTED_REGISTRY_PATH).read_bytes()
    )
    source_rows = [
        row
        for row in registry["source_authority_manifest"]
        if row.get("dictionary_role") in builder.SOURCE_ROLES
    ]
    expected_by_path = {row["path"]: row["sha256"] for row in source_rows}
    observed = []

    def hash_with_last_source_failure(path):
        relative = str(path.relative_to(PSID_ROOT))
        observed.append(relative)
        if len(observed) == builder.EXPECTED_REGISTERED_SOURCE_COUNT:
            return "0" * 64
        return expected_by_path[relative]

    semantic_calls = 0

    def unexpected_semantic_call():
        nonlocal semantic_calls
        semantic_calls += 1
        return "26.04.0"

    monkeypatch.setattr(builder, "_sha256_file", hash_with_last_source_failure)
    monkeypatch.setattr(
        builder.extraction, "pdftotext_version", unexpected_semantic_call
    )
    with pytest.raises(builder.BuildError, match="source SHA-256 mismatch"):
        builder.fresh_build(
            REPOSITORY_ROOT / builder.EXPECTED_REGISTRY_PATH, PSID_ROOT
        )
    assert len(observed) == builder.EXPECTED_REGISTERED_SOURCE_COUNT
    assert observed[-1] == source_rows[-1]["path"]
    assert semantic_calls == 0


def test_worker_rejects_implementation_identity_drift(tmp_path):
    tmp_path.chmod(0o700)
    capability = "a" * 64
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(
        builder.canonical_json_bytes(
            {
                "implementation_identity": {"drift": True},
                "projected": [{} for _ in range(47)],
                "registered": [{} for _ in range(47)],
                "worker_capability": capability,
            }
        )
    )
    output = tmp_path / "summary-0.json"
    with pytest.raises(builder.BuildError, match="implementation identity"):
        builder.main(
            [
                "--worker-manifest",
                str(manifest),
                "--worker-output",
                str(output),
                "--worker-position",
                "0",
                "--worker-member-offset",
                "0",
                "--worker-capability",
                capability,
                "--psid-root",
                str(PSID_ROOT),
            ]
        )
    assert not output.exists()
