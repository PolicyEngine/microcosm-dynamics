"""Invented hash-manifest tests; no runtime population or source fetches."""

from pathlib import Path

import pytest

from populace_dynamics.track_a_v2.manifest import (
    INVENTED_HEADER,
    SPECIFICATION_SHA256,
    build_manifest,
    object_sha256,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]


def manifest(tmp_path, **changes):
    input_path = tmp_path / "invented-input.json"
    input_path.write_text(
        '{"header":"INVENTED DATA - NOT A COMPARISON","n":2}\n'
    )
    return build_manifest(
        root=ROOT,
        implementation=[Path("src/populace_dynamics/track_a_v2/manifest.py")],
        inputs={"invented": input_path},
        parameter_bundles={"invented": {"nawi": {"1987": 100}}},
        invented=True,
        **changes,
    )


def test_manifest_covers_every_required_hash_category(tmp_path):
    """Spec, code, inputs, parameters, A1/E1 and source records are bound."""
    record = manifest(tmp_path)
    verify_manifest(record, root=ROOT)
    assert record["header"] == INVENTED_HEADER
    assert record["specification"]["sha256"] == SPECIFICATION_SHA256
    assert set(record["parameter_blocks"]) == {"A1", "E1"}
    assert set(record["source_records"]["poms"]) == {
        "RS 00615.260",
        "GN 00204.035",
    }
    assert record["source_records"]["statute"]["sha256"]
    assert record["implementation"][0]["sha256"]
    assert record["parameter_bundles"]["invented"]["sha256"]


def test_manifest_is_deterministic_and_detects_input_changes(tmp_path):
    """Mapping order cannot change a digest; changing input bytes must."""
    record = manifest(tmp_path)
    assert record == manifest(tmp_path)
    assert object_sha256({"x": 1, "y": 2}) == object_sha256({"y": 2, "x": 1})
    (tmp_path / "invented-input.json").write_text("changed\n")
    with pytest.raises(ValueError, match="file differs"):
        verify_manifest(record, root=ROOT)


def test_historical_poms_hashes_are_provenance_not_a_new_fetch(tmp_path):
    """Unprovided archived POMS bytes are never falsely marked verified."""
    record = manifest(tmp_path)
    assert all(
        not item["archived_bytes_independently_rehashed"]
        for item in record["source_records"]["poms"].values()
    )
    assert record["source_files"] == {}


def test_wrong_source_bytes_are_refused(tmp_path):
    """Intended mutation: invented source bytes cannot impersonate statute."""
    fake_source = tmp_path / "invented-statute.txt"
    fake_source.write_text("INVENTED DATA - NOT A COMPARISON\n")
    with pytest.raises(ValueError, match="source bytes differ"):
        manifest(tmp_path, source_files={"statute": fake_source})


def test_manifest_script_writes_invented_exclusively(tmp_path):
    """The script computes its manifest and never overwrites an artifact."""
    import json

    from scripts.track_a_v2_hash_manifest import main

    data = tmp_path / "invented.json"
    data.write_text('{"header":"INVENTED DATA - NOT A COMPARISON"}')
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "inputs": {"invented": str(data)},
                "parameter_bundles": {"invented": {"rate": 0}},
            }
        )
    )
    output = tmp_path / "manifest.json"
    args = ["--invented", "--request", str(request), "--output", str(output)]
    assert main(args) == 0
    result = json.loads(output.read_text())
    assert result["header"] == INVENTED_HEADER
    verify_manifest(result, root=ROOT)
    with pytest.raises(FileExistsError):
        main(args)
