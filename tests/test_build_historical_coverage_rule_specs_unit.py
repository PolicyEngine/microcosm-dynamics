"""Pure unit checks for the historical legal-registry builder."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_historical_coverage_rule_specs as builder  # noqa: E402

FIXTURE_ISSUER = "Fixture legislature"
FIXTURE_TIMESTAMP = "2026-08-02T00:00:00Z"


def _manifest_row(
    raw: bytes,
    *,
    filename: str = "source.pdf",
    declared_size: int | None = None,
    declared_sha256: str | None = None,
) -> bytes:
    size = len(raw) if declared_size is None else declared_size
    digest = (
        hashlib.sha256(raw).hexdigest()
        if declared_sha256 is None
        else declared_sha256
    )
    return (
        f"{FIXTURE_TIMESTAMP}\t{digest}\t{size}\t{filename}\t"
        f"https://example.gov/{filename}\n"
    ).encode()


def _configure_single_capture(
    monkeypatch: pytest.MonkeyPatch,
    manifest_raw: bytes,
    *,
    filename: str = "source.pdf",
    declared_source_size: int,
) -> None:
    monkeypatch.setattr(
        builder, "EXPECTED_CAPTURE_MANIFEST_SIZE", len(manifest_raw)
    )
    monkeypatch.setattr(
        builder,
        "EXPECTED_CAPTURE_MANIFEST_SHA256",
        hashlib.sha256(manifest_raw).hexdigest(),
    )
    monkeypatch.setattr(builder, "EXPECTED_CAPTURE_ROW_COUNT", 1)
    monkeypatch.setattr(
        builder, "EXPECTED_DECLARED_SOURCE_BYTE_SIZE", declared_source_size
    )
    monkeypatch.setattr(builder, "EXPECTED_SOURCE_DOCUMENT_CANDIDATE_COUNT", 1)
    monkeypatch.setattr(builder, "EXPECTED_REJECTED_SOURCE_DOCUMENT_COUNT", 0)
    monkeypatch.setattr(
        builder,
        "REVIEWED_SOURCE_METADATA",
        {filename: (FIXTURE_ISSUER, "federal_statute")},
    )
    monkeypatch.setattr(builder, "REJECTED_SOURCE_METADATA", {})


def _write_mode_0644(path: Path, raw: bytes) -> None:
    path.write_bytes(raw)
    path.chmod(0o644)


def _single_capture_fixture(
    capture_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[bytes, Path, Path]:
    capture_root.mkdir(parents=True)
    source_raw = b"%PDF-fixture\n"
    manifest_raw = _manifest_row(source_raw)
    _configure_single_capture(
        monkeypatch,
        manifest_raw,
        declared_source_size=len(source_raw),
    )
    manifest_path = capture_root / builder.CAPTURE_MANIFEST_FILENAME
    source_path = capture_root / "source.pdf"
    _write_mode_0644(manifest_path, manifest_raw)
    _write_mode_0644(source_path, source_raw)
    return manifest_raw, manifest_path, source_path


def _minimal_registry() -> dict:
    value = dict.fromkeys(builder.REGISTRY_TOP_LEVEL_FIELDS)
    value.update(
        {
            "schema_version": builder.TARGET_REGISTRY_SCHEMA_VERSION,
            "artifact_id": builder.TARGET_REGISTRY_SCHEMA_VERSION,
            "artifact_vintage_id": (
                builder.TARGET_REGISTRY_ARTIFACT_VINTAGE_ID
            ),
        }
    )
    return value


def test_builder_import_is_source_only_in_a_fresh_interpreter():
    source = f"""
import sys
sys.path.insert(0, {str(SCRIPTS)!r})
import build_historical_coverage_rule_specs as builder
assert str(builder.ROOT) == {str(ROOT)!r}
assert not any(
    name == 'populace_dynamics' or name.startswith('populace_dynamics.')
    for name in sys.modules
)
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", source],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_canonical_json_freezes_ascii_sorting_compaction_and_lf():
    assert (
        builder.canonical_json_bytes(
            {
                "z": "caf\N{LATIN SMALL LETTER E WITH ACUTE}",
                "a": [1, True, None],
            }
        )
        == b'{"a":[1,true,null],"z":"caf\\u00e9"}\n'
    )


@pytest.mark.parametrize(
    "value",
    [
        {"value": 0.25},
        {"value": float("nan")},
        {"value": (1, 2)},
        {1: "non-string-key"},
    ],
    ids=["finite-float", "nan", "tuple", "non-string-key"],
)
def test_canonical_json_rejects_values_outside_the_frozen_model(value):
    with pytest.raises(ValueError):
        builder.canonical_json_bytes(value)


def test_strict_parser_accepts_only_the_canonical_integer_json_form():
    raw = b'{"array":[-7,0,42],"text":"ok"}\n'
    assert builder.strict_json_loads(raw, "fixture") == {
        "array": [-7, 0, 42],
        "text": "ok",
    }


@pytest.mark.parametrize(
    "raw",
    [
        b'{"field":1,"field":2}\n',
        b'\xef\xbb\xbf{"field":1}\n',
        b'{"field":1.0}\n',
        b'{"field":1e0}\n',
        b'{"field":NaN}\n',
        b'{"field":-0}\n',
        b'{ "field":1}\n',
        b'{"field":1}\n\n',
        b'{"field":1}\ntrailing',
        b'{"field":"caf\xc3\xa9"}\n',
        b'{"field":"\xff"}\n',
    ],
    ids=[
        "duplicate-key",
        "bom",
        "decimal-float",
        "exponent-float",
        "nonfinite",
        "negative-zero",
        "whitespace",
        "extra-lf",
        "trailing-data",
        "alternate-unicode-escape",
        "invalid-utf8",
    ],
)
def test_strict_parser_rejects_every_ambiguous_or_noncanonical_form(raw):
    with pytest.raises(ValueError):
        builder.strict_json_loads(raw, "fixture")


def test_legal_rule_input_identity_has_the_exact_four_literals_and_full_sha():
    raw = builder.canonical_json_bytes(_minimal_registry())
    assert builder.legal_rule_input_identity(raw) == {
        "path": builder.TARGET_REGISTRY_PATH,
        "artifact_vintage_id": builder.TARGET_REGISTRY_ARTIFACT_VINTAGE_ID,
        "schema_version": builder.TARGET_REGISTRY_SCHEMA_VERSION,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


@pytest.mark.parametrize(
    "mutation",
    ["extra-key", "schema", "artifact-id", "vintage"],
)
def test_legal_rule_input_identity_rejects_envelope_or_literal_drift(mutation):
    value = _minimal_registry()
    if mutation == "extra-key":
        value["alias"] = "forbidden"
    elif mutation == "schema":
        value["schema_version"] = "historical_coverage_rule_specs.v2"
    elif mutation == "artifact-id":
        value["artifact_id"] = "alias"
    elif mutation == "vintage":
        value["artifact_vintage_id"] = "latest"
    with pytest.raises(ValueError):
        builder.legal_rule_input_identity(builder.canonical_json_bytes(value))


def test_build_registry_surfaces_every_fail_closed_category(monkeypatch):
    monkeypatch.setattr(
        builder,
        "build_registration_required_audit",
        lambda capture_root=builder.DEFAULT_CAPTURE_ROOT: {
            "dependency_rows": [{"dependency_id": "inventory"}],
            "source_gap_rows": [{"gap_id": "missing-statute"}],
            "evidence_constraint_rows": [
                {"constraint_id": "missing-transform-fact"}
            ],
        },
    )
    with pytest.raises(builder.RegistrationRequiredError) as error:
        builder.build_registry()
    assert error.value.dependency_ids == ("inventory",)
    assert error.value.source_gap_ids == ("missing-statute",)
    assert error.value.evidence_constraint_ids == ("missing-transform-fact",)
    assert error.value.registration_required_ids == (
        "inventory",
        "missing-statute",
        "missing-transform-fact",
    )


def test_syntax_validation_cannot_open_terminal_registry_emission_gate(
    monkeypatch,
):
    monkeypatch.setattr(
        builder,
        "build_registration_required_audit",
        lambda capture_root=builder.DEFAULT_CAPTURE_ROOT: {
            "dependency_rows": [],
            "source_gap_rows": [],
            "evidence_constraint_rows": [],
        },
    )

    with pytest.raises(builder.RegistrationRequiredError) as error:
        builder.build_registry()
    assert error.value.registration_required_ids == ()
    assert not (builder.ROOT / builder.TARGET_REGISTRY_PATH).exists()


def test_full_file_locator_freezes_complete_staged_identity():
    raw = b"registered bytes"
    digest = hashlib.sha256(raw).hexdigest()
    assert builder._full_file_locator("source.pdf", raw) == {
        "location_type": "full_file_byte_range",
        "filename": "source.pdf",
        "full_file_sha256": digest,
        "size_bytes": len(raw),
        "byte_start": 0,
        "byte_end": len(raw),
        "range_sha256": digest,
    }


def test_staged_manifest_must_exist_as_a_regular_file(tmp_path, monkeypatch):
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    source_raw = b"%PDF-fixture\n"
    manifest_raw = _manifest_row(source_raw)
    _configure_single_capture(
        monkeypatch,
        manifest_raw,
        declared_source_size=len(source_raw),
    )
    with pytest.raises(
        ValueError, match="capture_manifest.tsv is unavailable"
    ):
        builder._verified_capture(capture_root)


def test_staged_manifest_symlink_is_rejected(tmp_path, monkeypatch):
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    source_raw = b"%PDF-fixture\n"
    manifest_raw = _manifest_row(source_raw)
    _configure_single_capture(
        monkeypatch,
        manifest_raw,
        declared_source_size=len(source_raw),
    )
    manifest_target = tmp_path / "manifest-target.tsv"
    manifest_target.write_bytes(manifest_raw)
    (capture_root / builder.CAPTURE_MANIFEST_FILENAME).symlink_to(
        manifest_target
    )
    with pytest.raises(
        ValueError, match="capture_manifest.tsv is unavailable"
    ):
        builder._verified_capture(capture_root)


def test_staged_manifest_must_match_frozen_identity(tmp_path, monkeypatch):
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    source_raw = b"%PDF-fixture\n"
    manifest_raw = _manifest_row(source_raw)
    _configure_single_capture(
        monkeypatch,
        manifest_raw,
        declared_source_size=len(source_raw),
    )
    _write_mode_0644(
        capture_root / builder.CAPTURE_MANIFEST_FILENAME,
        b"x" * len(manifest_raw),
    )
    with pytest.raises(ValueError, match="staged identity mismatch"):
        builder._verified_capture(capture_root)


@pytest.mark.parametrize(
    "manifest_raw, row_count, total_bytes, metadata",
    [
        (
            _manifest_row(b"%PDF-fixture\n", filename="../source.pdf"),
            1,
            len(b"%PDF-fixture\n"),
            {"../source.pdf": (FIXTURE_ISSUER, "federal_statute")},
        ),
        (
            _manifest_row(b"%PDF-fixture\n") * 2,
            2,
            2 * len(b"%PDF-fixture\n"),
            {"source.pdf": (FIXTURE_ISSUER, "federal_statute")},
        ),
        (
            b"too\tfew\tcolumns\n",
            1,
            len(b"%PDF-fixture\n"),
            {"source.pdf": (FIXTURE_ISSUER, "federal_statute")},
        ),
    ],
    ids=["unsafe-filename", "duplicate-row", "malformed-row"],
)
def test_capture_manifest_rejects_unsafe_duplicate_or_malformed_rows(
    manifest_raw,
    row_count,
    total_bytes,
    metadata,
    monkeypatch,
):
    monkeypatch.setattr(builder, "EXPECTED_CAPTURE_ROW_COUNT", row_count)
    monkeypatch.setattr(
        builder, "EXPECTED_DECLARED_SOURCE_BYTE_SIZE", total_bytes
    )
    monkeypatch.setattr(builder, "REVIEWED_SOURCE_METADATA", metadata)
    monkeypatch.setattr(builder, "REJECTED_SOURCE_METADATA", {})
    with pytest.raises(ValueError):
        builder._capture_manifest_rows(manifest_raw)


@pytest.mark.parametrize("mutation", ["missing", "symlink", "size", "sha"])
def test_source_bytes_are_verified_before_media_classification(
    mutation, tmp_path, monkeypatch
):
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    source_raw = b"%PDF-fixture\n"
    manifest_raw = _manifest_row(source_raw)
    _configure_single_capture(
        monkeypatch,
        manifest_raw,
        declared_source_size=len(source_raw),
    )
    _write_mode_0644(
        capture_root / builder.CAPTURE_MANIFEST_FILENAME,
        manifest_raw,
    )
    source_path = capture_root / "source.pdf"
    if mutation == "symlink":
        target = tmp_path / "source-target.pdf"
        _write_mode_0644(target, source_raw)
        source_path.symlink_to(target)
    elif mutation == "size":
        _write_mode_0644(source_path, source_raw + b"x")
    elif mutation == "sha":
        _write_mode_0644(source_path, source_raw[:-2] + b"x\n")

    classified: list[bytes] = []

    def observe(raw: bytes) -> str:
        classified.append(raw)
        return "application/pdf"

    monkeypatch.setattr(builder, "_observed_media_type", observe)
    with pytest.raises(ValueError):
        builder._verified_capture(capture_root)
    assert classified == []


def test_verified_capture_uses_only_manifested_rows(tmp_path, monkeypatch):
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    source_raw = b"%PDF-fixture\n"
    manifest_raw = _manifest_row(source_raw)
    _configure_single_capture(
        monkeypatch,
        manifest_raw,
        declared_source_size=len(source_raw),
    )
    _write_mode_0644(
        capture_root / builder.CAPTURE_MANIFEST_FILENAME,
        manifest_raw,
    )
    _write_mode_0644(capture_root / "source.pdf", source_raw)
    (capture_root / "ambient-unmanifested.pdf").write_bytes(b"ignored")

    manifest, candidates, rejected = builder._verified_capture(capture_root)
    digest = hashlib.sha256(source_raw).hexdigest()
    assert manifest == {
        "locator": builder._full_file_locator(
            builder.CAPTURE_MANIFEST_FILENAME, manifest_raw
        ),
        "row_count": 1,
        "declared_source_byte_size": len(source_raw),
    }
    assert rejected == []
    assert len(candidates) == 1
    assert candidates[0]["manifest_position"] == 1
    assert candidates[0]["locator"] == builder._full_file_locator(
        "source.pdf", source_raw
    )
    assert candidates[0]["sha256"] == digest


@pytest.mark.parametrize("target", ["manifest", "payload"])
@pytest.mark.parametrize("mode", [0o600, 0o755])
def test_staged_manifest_and_payload_require_exact_mode_0644(
    target, mode, tmp_path, monkeypatch
):
    capture_root = tmp_path / "capture"
    _, manifest_path, source_path = _single_capture_fixture(
        capture_root, monkeypatch
    )
    {"manifest": manifest_path, "payload": source_path}[target].chmod(mode)

    with pytest.raises(ValueError, match="mode 0644"):
        builder._verified_capture(capture_root)


@pytest.mark.parametrize("target", ["manifest", "payload"])
def test_staged_manifest_and_payload_reject_hardlinks(
    target, tmp_path, monkeypatch
):
    capture_root = tmp_path / "capture"
    _, manifest_path, source_path = _single_capture_fixture(
        capture_root, monkeypatch
    )
    target_path = {"manifest": manifest_path, "payload": source_path}[target]
    os.link(target_path, tmp_path / f"{target}-hardlink")

    with pytest.raises(ValueError, match="link count must be one"):
        builder._verified_capture(capture_root)


@pytest.mark.parametrize("target", ["manifest", "payload"])
@pytest.mark.parametrize("kind", ["fifo", "directory"])
def test_staged_manifest_and_payload_reject_nonregular_files(
    target, kind, tmp_path, monkeypatch
):
    capture_root = tmp_path / "capture"
    _, manifest_path, source_path = _single_capture_fixture(
        capture_root, monkeypatch
    )
    target_path = {"manifest": manifest_path, "payload": source_path}[target]
    target_path.unlink()
    if kind == "fifo":
        os.mkfifo(target_path, mode=0o644)
    else:
        target_path.mkdir(mode=0o644)

    with pytest.raises(ValueError, match="regular file"):
        builder._verified_capture(capture_root)


@pytest.mark.parametrize("symlink_position", ["root", "intermediate"])
def test_capture_path_rejects_symlinked_root_or_intermediate(
    symlink_position, tmp_path, monkeypatch
):
    real_parent = tmp_path / "real-parent"
    capture_root = real_parent / "capture"
    _single_capture_fixture(capture_root, monkeypatch)
    if symlink_position == "root":
        supplied_root = tmp_path / "capture-link"
        supplied_root.symlink_to(capture_root, target_is_directory=True)
    else:
        linked_parent = tmp_path / "linked-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        supplied_root = linked_parent / "capture"

    with pytest.raises(ValueError, match="root.*symlinked"):
        builder._verified_capture(supplied_root)


@pytest.mark.parametrize("target", ["manifest", "payload"])
def test_staged_name_replacement_during_read_is_rejected(
    target, tmp_path, monkeypatch
):
    capture_root = tmp_path / "capture"
    manifest_raw, manifest_path, source_path = _single_capture_fixture(
        capture_root, monkeypatch
    )
    target_path = {"manifest": manifest_path, "payload": source_path}[target]
    target_raw = manifest_raw if target == "manifest" else b"%PDF-fixture\n"
    target_inode = target_path.stat().st_ino
    replacement = tmp_path / f"{target}-replacement"
    _write_mode_0644(replacement, target_raw)
    original_read = os.read
    replaced = False

    def replace_named_leaf(file_descriptor: int, size: int) -> bytes:
        nonlocal replaced
        if not replaced and os.fstat(file_descriptor).st_ino == target_inode:
            replacement.replace(target_path)
            replaced = True
        return original_read(file_descriptor, size)

    monkeypatch.setattr(builder.os, "read", replace_named_leaf)
    with pytest.raises(ValueError, match="changed during sealed read"):
        builder._verified_capture(capture_root)
    assert replaced


def test_descriptor_relative_opens_use_required_security_flags(
    tmp_path, monkeypatch
):
    capture_root = tmp_path / "capture"
    _single_capture_fixture(capture_root, monkeypatch)
    original_open = os.open
    calls: list[tuple[object, int, int | None]] = []

    def record_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        calls.append((path, flags, dir_fd))
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(builder.os, "open", record_open)
    builder._verified_capture(capture_root)

    assert calls[0][0] == "/"
    assert calls[0][2] is None
    assert all(dir_fd is not None for _, _, dir_fd in calls[1:])
    directory_calls = [call for call in calls if call[1] & os.O_DIRECTORY]
    leaf_calls = [call for call in calls if not call[1] & os.O_DIRECTORY]
    assert directory_calls
    assert {call[0] for call in leaf_calls} == {
        builder.CAPTURE_MANIFEST_FILENAME,
        "source.pdf",
    }
    for _, flags, _ in directory_calls:
        assert flags & os.O_NOFOLLOW
        assert flags & os.O_CLOEXEC
    for _, flags, _ in leaf_calls:
        assert flags & os.O_NOFOLLOW
        assert flags & os.O_NONBLOCK
        assert flags & os.O_CLOEXEC


def test_leaf_swap_to_fifo_between_stat_and_open_cannot_block(
    tmp_path, monkeypatch
):
    capture_root = tmp_path / "capture"
    _single_capture_fixture(capture_root, monkeypatch)
    source_path = capture_root / "source.pdf"
    original_open = os.open
    swapped = False

    def replace_with_fifo_before_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if path == "source.pdf" and not swapped:
            source_path.unlink()
            os.mkfifo(source_path, mode=0o644)
            swapped = True
            assert flags & os.O_NONBLOCK
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(builder.os, "open", replace_with_fifo_before_open)
    with pytest.raises(ValueError, match="changed during sealed open"):
        builder._verified_capture(capture_root)
    assert swapped
