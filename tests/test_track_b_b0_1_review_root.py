"""Tests for the Q6 review-root builder and read log, on invented files.

No repository file on the exclusion list is opened: the pieces are
exercised on a temporary directory with invented content.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_review_root as review_root  # noqa: E402


def _invented_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    files = {
        "docs/keep.md": "kept text",
        "docs/denied.md": "invented boundary text",
        "gates.yaml": "invented: 1",
        f"{review_root.CODEBOOK_DIR}/a.json": '{"code_map": []}',
        "data/other_codebook.json": '{"code_map_columns": ["frequency"]}',
        "data/plain.json": '{"frequency_of_use": 3}',
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def test_denied_paths_are_whole_files_whatever_the_scope():
    inventories = [
        {
            "q6_exclusions": [
                {"path": "gates.yaml", "scope": "lines", "lines": [[1, 2]]},
                {"path": "docs/denied.md", "scope": "whole_file"},
            ]
        },
        {"q6_exclusions": [{"path": "gates.yaml", "scope": "whole_file"}]},
    ]
    assert review_root.denied_paths(inventories) == [
        "docs/denied.md",
        "gates.yaml",
    ]


def test_removal_and_codebook_check(tmp_path):
    root = _invented_root(tmp_path)
    removed = review_root.remove_denied(root, ["docs/denied.md", "gates.yaml"])
    assert removed == [
        f"{review_root.CODEBOOK_DIR}/a.json",
        "docs/denied.md",
        "gates.yaml",
    ]
    assert not (root / review_root.CODEBOOK_DIR).exists()
    assert review_root.codebook_tables(root) == ["data/other_codebook.json"]
    assert (
        review_root.codebook_tables(root, ["data/other_codebook.json"]) == []
    )
    (root / "data/other_codebook.json").unlink()
    assert review_root.codebook_tables(root) == []
    files = review_root.manifest(root)
    assert set(files) == {"docs/keep.md", "data/plain.json"}


def test_read_log_flags_paths_outside_the_root_or_denied(tmp_path):
    root = _invented_root(tmp_path)
    outside = tmp_path / "elsewhere.md"
    outside.write_text("x", encoding="utf-8")

    def event(block):
        return json.dumps({"message": {"content": [block]}})

    lines = [
        event(
            {
                "type": "tool_use",
                "name": "Read",
                "input": {"file_path": str(root / "docs/keep.md")},
            }
        ),
        event(
            {
                "type": "tool_use",
                "name": "Grep",
                "input": {"pattern": "bound", "path": str(root)},
            }
        ),
        event(
            {
                "type": "tool_result",
                "content": [
                    {"type": "text", "text": f"{root}/docs/keep.md:1:kept"}
                ],
            }
        ),
        "not json",
    ]
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(lines), encoding="utf-8")
    clean = review_root.read_log(transcript, root, ["docs/denied.md"])
    assert clean["review_counts"] is True
    assert clean["n_tool_calls"] == 2
    assert set(clean["paths"].values()) == {"inside_root"}
    # The log holds paths, never result text.
    assert "kept" not in json.dumps(clean["tool_calls"])

    for bad_path, kind in (
        (str(outside), "outside_root"),
        (str(root / "docs/denied.md"), "denied"),
        (str(root / review_root.CODEBOOK_DIR / "a.json"), "denied"),
    ):
        transcript.write_text(
            "\n".join(
                [
                    *lines,
                    event(
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": bad_path},
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )
        flagged = review_root.read_log(transcript, root, ["docs/denied.md"])
        assert flagged["review_counts"] is False
        assert flagged["paths"][bad_path] == kind

    # A denied path that only a tool result returned also voids the review.
    transcript.write_text(
        "\n".join(
            [
                *lines,
                event(
                    {
                        "type": "tool_result",
                        "content": f"{outside}:3: text",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    assert review_root.read_log(transcript, root, [])["review_counts"] is False


def test_allow_list_is_limited_to_the_pull_request_s_files(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        review_root, "changed_files", lambda base, head: {"scripts/mine.py"}
    )
    with pytest.raises(ValueError, match="needs --base"):
        review_root.build("h", tmp_path / "r", [], {}, allowed=["x"])
    with pytest.raises(ValueError, match="not changed by this pull request"):
        review_root.build(
            "h", tmp_path / "r", [], {}, allowed=["gates.yaml"], base="b"
        )
    assert not (tmp_path / "r").exists()
