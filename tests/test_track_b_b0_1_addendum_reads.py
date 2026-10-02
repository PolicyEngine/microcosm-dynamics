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
        [
            "named_only_as_excluded_pathspec_or_range",
            "scope_printed_nothing_from_excluded",
        ],
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
            "command",
            "scope_names_or_counts_only",
            "scope_output_lines_from_excluded_files",
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
    flagged = [record["calls"][i] for i in record["flagged_call_indices"]]
    words = {3: "three", 7: "seven", 11: "Eleven"}
    by_hand = sum(1 for call in flagged if "flag_note" in call)
    assert f"{words[by_hand]} are classified by hand" in prose
    freeze = "2026-10-01T03:58:18"

    def scoped(who):
        return [
            call
            for call in flagged
            if (call["agent"] == "main") == (who == "main")
            and call["utc"] < freeze
            and any(c.startswith("scope_") for c in call["flag_class"])
        ]

    assert len(scoped("main")) == 3
    assert all(
        c["flag_class"] == ["scope_printed_nothing_from_excluded"]
        for c in scoped("main")
    )
    agents = scoped("agents")
    assert f"{words[len(agents)]} of their recursive or glob searches" in prose
    counts = {
        k: sum(1 for c in agents if k in c["flag_class"])
        for k in (
            "scope_printed_nothing_from_excluded",
            "scope_printed_names_or_counts_only",
            "scope_no_result_in_transcript",
        )
    }
    assert counts == {
        "scope_printed_nothing_from_excluded": 7,
        "scope_printed_names_or_counts_only": 3,
        "scope_no_result_in_transcript": 1,
    }


def _paired_export(tmp_path, pairs):
    """An export whose Bash calls each carry their own output."""
    lines = []
    for i, (command, output) in enumerate(pairs):
        use = {
            "type": "tool_use",
            "id": f"b{i}",
            "name": "Bash",
            "input": {"command": command},
        }
        result = {"type": "tool_result", "tool_use_id": f"b{i}"}
        result["content"] = output
        lines.append(
            json.dumps(
                {
                    "timestamp": "2026-10-01T00:00:00Z",
                    "message": {"content": [use]},
                }
            )
        )
        lines.append(json.dumps({"message": {"content": [result]}}))
    path = tmp_path / "paired.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("transcript.jsonl", "\n".join(lines))
    return path


def test_recursive_and_glob_scopes_are_flagged_with_output_counts(
    tmp_path, checker
):
    wt = "/Users/maxghenis/PolicyEngine" + reads.WORKTREE_MARK
    search = "grep -" + "r"
    pairs = [
        (f"cd {wt} && {search}n bound .", "gates.yaml:12:x\nsrc/a.py:3:y"),
        (f"cd {wt} && {search}l bound .", "gates.yaml\nsrc/a.py"),
        (f"cd {wt} && {search}n bound . | grep -v '^gates'", "src/a.py:3:y"),
        (f"cd {wt} && grep -n x docs/design/*.md", "docs/design/b.md:1:z"),
        (f"cd {wt} && {search}n x --include='*.py' .", "src/a.py:1:z"),
        (
            f"cd {wt} && git grep -c x -- . ':!gates.yaml' "
            "':!docs/design/m6_*' "
            "':!data/external/psid_codebook_field_evidence'",
            "src/a.py:1",
        ),
        (f"cd {wt} && git grep -c x -- . ':!gates.yaml'", "src/a.py:1"),
        (f"cd /Users/x/other-repo && {search}n bound .", "a.py:1:z"),
        (f"W={wt}; cd $W && {search}l bound .", "src/a.py"),
    ]
    with zipfile.ZipFile(_paired_export(tmp_path, pairs)) as archive:
        found = reads.extract(archive, checker)
    calls = found["calls"]
    assert calls[0]["flag_class"] == ["OTHER_scope_printed_excluded_lines"]
    assert calls[0]["scope_output_lines_from_excluded_files"] == 1
    assert calls[1]["flag_class"] == ["scope_printed_names_or_counts_only"]
    assert calls[2]["flag_class"] == ["scope_printed_nothing_from_excluded"]
    assert "scope:docs/design/m6_projection_engine.md" in calls[3]["flags"]
    assert calls[3]["flag_class"] == ["scope_printed_nothing_from_excluded"]
    assert "flags" not in calls[4]
    assert calls[5]["flag_class"] == [
        "named_only_as_excluded_pathspec_or_range"
    ]
    assert not any(f.startswith("scope:") for f in calls[5]["flags"])
    assert "scope:docs/design/m6_projection_engine.md" in calls[6]["flags"]
    assert calls[6]["flag_class"] == [
        "named_only_as_excluded_pathspec_or_range",
        "scope_printed_nothing_from_excluded",
    ]
    assert "flags" not in calls[7]
    assert "scope:gates.yaml" in calls[8]["flags"]
    for index in found["flagged_call_indices"]:
        assert calls[index]["command"] == pairs[index][0]
    assert "12:x" not in json.dumps(found)
