"""B2's outcome files stay out of every blinded review root.

B2's run record (PR #547) and the cumulative attempt ledger (PR #548) hold
reference-year 2012 and 2014 floor values, truth moments and B2's candidate
outcome. No exposure-inventory scan lists them, so
``docs/design/track_b_b2_outcome_exclusions.json`` is a standing exclusion
record that ``scripts/track_b_b0_1_review_root.py`` applies to every build,
whatever inventories the build names.
"""

from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_review_root as review_root  # noqa: E402

RECORD = ROOT / "docs" / "design" / "track_b_b2_outcome_exclusions.json"
B2_OUTCOME_FILES = {
    "docs/design/track_b_attempt_ledger.md",
    "runs/track_b_b2_floor.json",
    "runs/track_b_b2_floor_v1_stopped.json",
    "runs/track_b_b2_score.attempt.jsonl",
    "runs/track_b_b2_score.json",
}


def test_the_standing_record_lists_b2s_outcome_files():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["schema"] == "track_b_b2_outcome_exclusions.v1"
    entries = record["q6_exclusions"]
    assert {entry["path"] for entry in entries} == B2_OUTCOME_FILES
    assert all(entry["scope"] == "whole_file" for entry in entries)
    for relative in B2_OUTCOME_FILES:
        assert (ROOT / relative).is_file(), relative
    assert review_root.STANDING_EXCLUSIONS == (
        "docs/design/track_b_b2_outcome_exclusions.json",
    )
    standing = review_root.standing_inventories()
    assert set(review_root.denied_paths(standing)) == B2_OUTCOME_FILES


def test_a_missing_standing_record_refuses_rather_than_drops(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(review_root, "STANDING_EXCLUSIONS", ("missing.json",))
    with pytest.raises(FileNotFoundError, match="missing.json"):
        review_root.standing_inventories(tmp_path)
    (tmp_path / "missing.json").write_text(
        json.dumps({"q6_exclusions": [{"path": "x.md"}]}), encoding="utf-8"
    )
    assert review_root.standing_inventories(tmp_path) == [
        {"q6_exclusions": [{"path": "x.md"}]}
    ]


def _archive_of(files: dict[str, str]):
    """A stand-in for ``git archive`` that writes ``files`` as a tar."""

    def run(command, cwd=None, check=False):
        archive = Path(command[command.index("-o") + 1])
        with tarfile.open(archive, "w") as tar:
            for relative, content in files.items():
                data = content.encode()
                info = tarfile.TarInfo(relative)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

    return SimpleNamespace(run=run)


def test_build_excludes_b2s_outcome_files_without_any_inventory(
    tmp_path, monkeypatch
):
    files = {relative: "invented" for relative in B2_OUTCOME_FILES}
    files["docs/keep.md"] = "kept text"
    monkeypatch.setattr(review_root, "subprocess", _archive_of(files))
    out = tmp_path / "root"
    record = review_root.build("h", out, [], {})
    assert B2_OUTCOME_FILES <= set(record["denied_paths"])
    assert B2_OUTCOME_FILES <= set(record["removed"])
    for relative in B2_OUTCOME_FILES:
        assert not (out / relative).exists(), relative
    assert (out / "docs/keep.md").is_file()
    assert set(review_root.manifest(out)) == {"docs/keep.md"}


def test_build_unions_named_and_standing_exclusions(tmp_path, monkeypatch):
    """A named inventory that repeats a standing path and names a path the
    archive lacks: the record denies the sorted union, removes only what
    the archive held, and keeps everything else."""
    files = {relative: "invented" for relative in B2_OUTCOME_FILES}
    files.update({"docs/keep.md": "kept text", "docs/named.md": "named"})
    monkeypatch.setattr(review_root, "subprocess", _archive_of(files))
    named = tmp_path / "named.json"
    named.write_text(
        json.dumps(
            {
                "q6_exclusions": [
                    {"path": "docs/named.md"},
                    {"path": "runs/track_b_b2_score.json"},
                    {"path": "docs/absent.md"},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "root"
    record = review_root.build("h", out, [named], {})
    expected = sorted(B2_OUTCOME_FILES | {"docs/named.md", "docs/absent.md"})
    assert record["denied_paths"] == expected
    assert record["removed"] == sorted(B2_OUTCOME_FILES | {"docs/named.md"})
    assert set(review_root.manifest(out)) == {"docs/keep.md"}


def test_a_missing_standing_record_leaves_no_partial_root(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(review_root, "STANDING_EXCLUSIONS", ("missing.json",))
    monkeypatch.setattr(
        review_root, "subprocess", _archive_of({"docs/keep.md": "kept"})
    )
    out = tmp_path / "root"
    with pytest.raises(FileNotFoundError, match="missing.json"):
        review_root.build("h", out, [], {})
    assert not out.exists()
    assert not (tmp_path / "root.tar").exists()


@settings(max_examples=100, deadline=None)
@given(
    st.lists(
        st.lists(
            st.sampled_from(
                [
                    "docs/a.md",
                    "gates.yaml",
                    "runs/track_b_b2_score.json",
                    "runs/other.json",
                ]
            ),
            max_size=4,
        ),
        max_size=4,
    )
)
def test_standing_paths_are_denied_whatever_the_inventories(named):
    inventories = [
        {"q6_exclusions": [{"path": path} for path in paths]}
        for paths in named
    ]
    denied = review_root.denied_paths(
        [*inventories, *review_root.standing_inventories()]
    )
    assert denied == sorted(set(denied))
    assert B2_OUTCOME_FILES <= set(denied)
    assert set(denied) == B2_OUTCOME_FILES | {
        path for paths in named for path in paths
    }
