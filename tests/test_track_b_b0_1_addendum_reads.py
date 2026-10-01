"""Tests for the addendum's reads-record extractor, on an invented export.

The export is built here from invented tool calls. No real transcript,
restricted file or excluded file is read.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_addendum_reads as reads  # noqa: E402

SECRET = "OUTPUT-THAT-MUST-NOT-BE-RECORDED"
OWN = "/Users/maxghenis" + reads.OWN_SUBFOLDER + "tool-results/x.txt"
OTHER = "/Users/maxghenis/.claude/projects/elsewhere/other-session/y.txt"


def _use(command=None, **given):
    if command is not None:
        given["command"] = command
    return {"type": "tool_use", "id": "t", "name": "Bash", "input": given}


def _read(path, offset=None, limit=None):
    given = {"file_path": path}
    if offset is not None:
        given["offset"] = offset
    if limit is not None:
        given["limit"] = limit
    return {"type": "tool_use", "id": "r", "name": "Read", "input": given}


def _export(tmp_path, blocks):
    lines = []
    for block in blocks:
        lines.append(
            json.dumps(
                {
                    "timestamp": "2026-10-01T00:00:00Z",
                    "message": {"role": "assistant", "content": [block]},
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": block["id"],
                                "content": SECRET + " gates.yaml",
                            }
                        ],
                    }
                }
            )
        )
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("transcript.jsonl", "\n".join(lines))
    return path


@pytest.fixture
def checker():
    return reads.Checker(
        restricted={"/Users/maxghenis/.claude/projects/"},
        denied={"gates.yaml", "docs/design/m6_projection_engine.md"},
        ranges={"gates.yaml": [(5775, 5785), (5888, 5896)]},
    )


def _classes(tmp_path, checker, blocks):
    with zipfile.ZipFile(_export(tmp_path, blocks)) as archive:
        found = reads.extract(archive, checker)
    return found, [
        found["calls"][i]["flag_class"] for i in found["flagged_call_indices"]
    ]


def test_no_tool_output_is_recorded(tmp_path, checker):
    found, _ = _classes(
        tmp_path, checker, [_use("ls docs"), _read("/w/scripts/a.py")]
    )
    assert SECRET not in json.dumps(found)
    assert [c["tool"] for c in found["calls"]] == ["Bash", "Read"]
    assert found["flagged_call_indices"] == []


def test_ranges_and_pathspecs_are_classified(tmp_path, checker):
    _, classes = _classes(
        tmp_path,
        checker,
        [
            _use("cd /w && sed -n 5500,5620p gates.yaml"),
            _use("cd /w && sed -n 5770,5790p gates.yaml"),
            _use("git grep -c X -- . ':!gates.yaml'"),
            _use("git diff --numstat a b -- gates.yaml"),
            _read("/w/gates.yaml", offset=5500, limit=130),
            _read("/w/gates.yaml", offset=5700, limit=200),
            _use('grep -rn "gates.yaml\\|ledger" src/ scripts/a.py | head'),
            _use("cd /w && cat gates.yaml | head"),
        ],
    )
    assert classes == [
        ["ranged_read_outside_flagged_ranges"],
        ["OTHER", "OTHER_sed_inside_flagged_range"],
        ["named_only_as_excluded_pathspec_or_range"],
        ["git_metadata_only"],
        ["ranged_read_outside_flagged_ranges"],
        ["OTHER_read"],
        ["named_in_grep_pattern_or_filter"],
        ["OTHER"],
    ]


def test_restricted_paths_split_own_subfolder_from_others(tmp_path, checker):
    _, classes = _classes(
        tmp_path, checker, [_read(OWN), _read(OTHER), _use(f"cat {OTHER}")]
    )
    assert classes == [
        ["own_transcript_subfolder"],
        ["OTHER_restricted"],
        ["OTHER_restricted"],
    ]


def test_restricted_prefixes_expand_the_list_s_abbreviations():
    text = "- `EV/a.pdf`\n- `REFS/b/`\n- `~/.claude/projects/x/`\n- `EV/`\n"
    out = reads.restricted_prefixes(text)
    assert out == {
        reads.EV + "/a.pdf",
        reads.REFS + "/b/",
        "/Users/maxghenis/.claude/projects/x/",
    }


def test_committed_record_has_no_unresolved_flag():
    record = json.loads(
        (ROOT / "docs/design/track_b_b0_1_addendum_reads.json").read_text()
    )
    assert record["n_calls"] == len(record["calls"])
    for index in record["flagged_call_indices"]:
        classes = record["calls"][index]["flag_class"]
        assert classes and not any(c.startswith("OTHER") for c in classes)
    for call in record["calls"]:
        assert set(call) <= {
            "agent",
            "utc",
            "tool",
            *reads.INPUT_KEYS,
            "command_first_line",
            "command_sha256",
            "paths_named",
            "flags",
            "flag_class",
            "flag_note",
        }


def test_addendum_states_the_record_s_counts():
    record = json.loads(
        (ROOT / "docs/design/track_b_b0_1_addendum_reads.json").read_text()
    )
    prose = " ".join(
        (ROOT / "docs/design/track_b_b0_1_addendum.md").read_text().split()
    )
    assert f"up to the export, {record['n_calls']:,} calls" in prose
    assert (
        f"flags the {len(record['flagged_call_indices'])} calls that name"
        in prose
    )
