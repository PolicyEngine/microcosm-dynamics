"""Tests for the Q6 review-root builder and read log, on invented files.

No repository file on the exclusion list is opened: the pieces are
exercised on a temporary directory with invented content.
"""

from __future__ import annotations

import inspect
import json
import random
import re
import shutil
import subprocess
import sys
from fnmatch import fnmatchcase
from itertools import pairwise
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

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


def test_read_log_ignores_quoted_paths_and_records_harness_notices(tmp_path):
    root = _invented_root(tmp_path)
    saved = "/Users/x/.claude/projects/lane/s/tool-results/t1.txt"

    def event(block):
        return json.dumps({"message": {"content": [block]}})

    def call(i, name, **given):
        return event(
            {"type": "tool_use", "id": i, "name": name, "input": given}
        )

    def result(i, text):
        return event(
            {"type": "tool_result", "tool_use_id": i, "content": text}
        )

    lines = [
        call("r", "Read", file_path=str(root / "docs/keep.md")),
        result("r", "1\tsee /Users/x/elsewhere/file.md and ~/y"),
        call("g", "Grep", pattern="x", path=str(root)),
        result("g", f"Output too large. Full output saved to: {saved}"),
        call("h", "Glob", pattern="**/*.md", path=str(root)),
        result("h", f"{root}/docs/keep.md"),
    ]
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(lines), encoding="utf-8")
    log = review_root.read_log(transcript, root, [])
    assert log["review_counts"] is True
    assert log["harness_persisted_outputs"] == [saved]
    assert log["persisted_outputs_opened"] == []
    assert set(log["paths"]) == {
        str(root / "docs/keep.md"),
        str(root),
        "pattern:**/*.md",
    }
    assert log["paths"]["pattern:**/*.md"] == "inside_root"

    lines += [call("o", "Read", file_path=saved)]
    transcript.write_text("\n".join(lines), encoding="utf-8")
    log = review_root.read_log(transcript, root, [])
    assert log["review_counts"] is False
    assert log["persisted_outputs_opened"] == [saved]


def _codex_transcript(tmp_path: Path, commands: list[str]) -> Path:
    lines = [json.dumps({"type": "thread.started"}), "not json"]
    for index, command in enumerate(commands):
        item = {
            "id": f"item_{index}",
            "type": "command_execution",
            "command": command,
        }
        lines.append(json.dumps({"type": "item.started", "item": item}))
        lines.append(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {**item, "aggregated_output": "/etc/passwd"},
                }
            )
        )
    path = tmp_path / "codex.jsonl"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_codex_read_log_counts_commands_inside_the_root(tmp_path):
    root = _invented_root(tmp_path)
    commands = [
        "/bin/zsh -lc \"nl -ba docs/keep.md | sed -n '1,20p'\"",
        "/bin/zsh -lc \"rg -n 'gates.yaml|bound' docs\"",
        "/bin/zsh -lc 'python3 -c \"import json; print(1)\" 2>/dev/null'",
        f"/bin/zsh -lc 'cat {root}/docs/keep.md'",
    ]
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, commands), root, ["docs/denied.md"]
    )
    # started and completed events of one item count once
    assert log["n_commands"] == 4
    assert log["review_counts"] is True
    assert log["paths_outside_root_or_denied"] == []
    # output is never read: the invented output names /etc/passwd
    assert "/etc/passwd" not in json.dumps(log)


@pytest.mark.parametrize(
    ("command", "kind"),
    [
        ("/bin/zsh -lc 'cat /etc/hosts'", "outside_root"),
        ("/bin/zsh -lc 'cat ../elsewhere.md'", "outside_root"),
        ("/bin/zsh -lc 'ls ~/PolicyEngine'", "outside_root"),
        ("/bin/zsh -lc 'cat $HOME/x'", "shell_expansion"),
        ("/bin/zsh -lc 'cd /tmp && ls'", "outside_root"),
        ('/bin/zsh -lc "rg --files=/var/x"', "outside_root"),
        ("/bin/zsh -lc 'nl -ba docs/../../elsewhere.md'", "outside_root"),
    ],
)
def test_codex_read_log_flags_paths_that_leave_the_root(
    tmp_path, command, kind
):
    root = _invented_root(tmp_path)
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, [command]), root, ["docs/denied.md"]
    )
    assert log["review_counts"] is False
    assert kind in log["flagged_kinds"].values()


def test_codex_read_log_flags_an_absolute_denied_path(tmp_path):
    root = _invented_root(tmp_path)
    command = f"/bin/zsh -lc 'cat {root}/docs/denied.md'"
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, [command]), root, ["docs/denied.md"]
    )
    assert log["review_counts"] is False
    assert list(log["flagged_kinds"].values()) == ["denied"]


@pytest.mark.parametrize(
    "command",
    [
        "/bin/zsh -lc 'cat $PWD/../elsewhere.md'",
        '/bin/zsh -lc "cat \\"$OLDPWD/x\\""',
        "/bin/zsh -lc 'cat ${HOME}/x'",
        "/bin/zsh -lc 'cat $(pwd)/x'",
        "/bin/zsh -lc 'cat `pwd`/x'",
    ],
)
def test_codex_read_log_voids_unresolved_shell_expansions(tmp_path, command):
    root = _invented_root(tmp_path)
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, [command]), root, ["docs/denied.md"]
    )
    assert log["review_counts"] is False


def test_codex_read_log_ignores_single_quoted_dollars(tmp_path):
    root = _invented_root(tmp_path)
    commands = [
        "/bin/zsh -lc \"sed -n '1,$p' docs/keep.md\"",
        "/bin/zsh -lc \"rg -n 'bound$' docs\"",
        "/bin/zsh -lc \"awk '{print $1}' docs/keep.md\"",
    ]
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, commands), root, ["docs/denied.md"]
    )
    assert log["review_counts"] is True


@pytest.mark.parametrize(
    "command",
    [
        # Q6 round 3: a nested shell expands its own script
        "/bin/zsh -lc \"sh -c 'cat $FILE'\"",
        "/bin/zsh -lc \"bash -c 'cat ${HOME}/x'\"",
        "/bin/zsh -lc \"eval 'cat $X'\"",
        # brace expansion and ANSI-C quoting
        "/bin/zsh -lc 'cat docs/{keep.md,../../elsewhere.md}'",
        "/bin/zsh -lc 'cat {/etc/hosts,docs/keep.md}'",
        "/bin/zsh -lc \"cat $'\\\\x2fetc/hosts'\"",
    ],
)
def test_codex_read_log_voids_nested_and_brace_escapes(tmp_path, command):
    root = _invented_root(tmp_path)
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, [command]), root, ["docs/denied.md"]
    )
    assert log["review_counts"] is False


def test_codex_read_log_does_not_treat_python_code_as_shell(tmp_path):
    """Round 3's own transcript: Python code quoted for the shell holds
    "$X" strings that no shell expands."""
    root = _invented_root(tmp_path)
    command = (
        '/bin/zsh -lc "python3 -c \'print(\\"cat $UNRESOLVED/x\\"); '
        'print(\\"sed -n 1,$p\\")\'"'
    )
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, [command]), root, ["docs/denied.md"]
    )
    assert log["review_counts"] is True


@pytest.mark.parametrize(
    ("command", "kind"),
    [
        # Q6 round 4's five escapes
        ("/bin/zsh -lc 'cat\t/invented-private/note.txt'", "outside_root"),
        (
            "/bin/zsh -lc \"bash -o errexit -c 'cat $FILE'\"",
            "shell_expansion",
        ),
        ("/bin/zsh -lc 'cat ~reviewer/invented.txt'", "outside_root"),
        ("/bin/zsh -lc 'cat =awk'", "shell_expansion"),
        ("/bin/zsh -lc 'cd; cat invented.txt'", "directory_change"),
        ("/bin/zsh -lc 'cat /usr/bin/invented-tool'", "outside_root"),
    ],
)
def test_codex_read_log_closes_round_4_escapes(tmp_path, command, kind):
    root = _invented_root(tmp_path)
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, [command]), root, ["docs/denied.md"]
    )
    assert log["review_counts"] is False
    assert kind in log["flagged_kinds"].values()


def test_codex_read_log_exempts_programs_only_in_program_position(tmp_path):
    root = _invented_root(tmp_path)
    commands = [
        "/bin/zsh -lc '/usr/bin/sed -n 1p docs/keep.md'",
        "/bin/zsh -lc 'X=1 /usr/bin/env python3 -c \"print(1)\" 2>/dev/null'",
        "/bin/zsh -lc 'nl -ba docs/keep.md | /usr/bin/head -n 3'",
    ]
    log = review_root.read_log_codex(
        _codex_transcript(tmp_path, commands), root, ["docs/denied.md"]
    )
    assert log["review_counts"] is True, log["flagged_kinds"]


def _claude_transcript(tmp_path, blocks):
    lines = [json.dumps({"message": {"content": [block]}}) for block in blocks]
    path = tmp_path / "claude.jsonl"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("blocks", "counts"),
    [
        # Q6 round 6: a Glob pattern naming a denied path, even one that
        # only confirms absence, voids the review
        (
            [
                {
                    "type": "tool_use",
                    "id": "g1",
                    "name": "Glob",
                    "input": {"pattern": "{gates.yaml,docs/denied.md}"},
                },
                {"type": "tool_result", "tool_use_id": "g1", "content": ""},
            ],
            False,
        ),
        # an absolute or escaping pattern voids it
        (
            [
                {
                    "type": "tool_use",
                    "id": "g2",
                    "name": "Glob",
                    "input": {"pattern": "../**/*.md"},
                }
            ],
            False,
        ),
        # a relative result path to a denied file voids it
        (
            [
                {
                    "type": "tool_use",
                    "id": "g3",
                    "name": "Grep",
                    "input": {"pattern": "bound", "glob": "*.md"},
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "g3",
                    "content": [
                        {"type": "text", "text": "docs/denied.md:3:bound"}
                    ],
                },
            ],
            False,
        ),
        # a relative result path that escapes voids it
        (
            [
                {
                    "type": "tool_use",
                    "id": "g4",
                    "name": "Glob",
                    "input": {"pattern": "*.md"},
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "g4",
                    "content": [{"type": "text", "text": "../elsewhere.md"}],
                },
            ],
            False,
        ),
        # Q6 round 7 L1: a nested denied file named by its basename, by its
        # stem before a dot, or the codebook directory by its last segment
        (
            [
                {
                    "type": "tool_use",
                    "id": "g6",
                    "name": "Glob",
                    "input": {"pattern": "**/deep_denied.md"},
                }
            ],
            False,
        ),
        (
            [
                {
                    "type": "tool_use",
                    "id": "g7",
                    "name": "Grep",
                    "input": {"pattern": "x", "glob": "{a.md,deep_denied.*}"},
                }
            ],
            False,
        ),
        (
            [
                {
                    "type": "tool_use",
                    "id": "g8",
                    "name": "Glob",
                    "input": {"pattern": "**/psid_codebook_field_evidence/*"},
                }
            ],
            False,
        ),
        # Q6 round 8 L1: a denied name split across a brace group, a
        # brace alternative that leaves the root, and a group too large
        # to expand
        (
            [
                {
                    "type": "tool_use",
                    "id": "g12",
                    "name": "Glob",
                    "input": {"pattern": "**/{deep_denied,x}.md"},
                }
            ],
            False,
        ),
        (
            [
                {
                    "type": "tool_use",
                    "id": "g13",
                    "name": "Grep",
                    "input": {
                        "pattern": "x",
                        "glob": "deep_{x,den{ied,y}}.md",
                    },
                }
            ],
            False,
        ),
        (
            [
                {
                    "type": "tool_use",
                    "id": "g14",
                    "name": "Glob",
                    "input": {"pattern": "{/etc,docs}/*.md"},
                }
            ],
            False,
        ),
        (
            [
                {
                    "type": "tool_use",
                    "id": "g15",
                    "name": "Glob",
                    "input": {"pattern": "{a,b}" * 13},
                }
            ],
            False,
        ),
        # an unbalanced group is literal to the tool; its pieces are
        # still read
        (
            [
                {
                    "type": "tool_use",
                    "id": "g16",
                    "name": "Glob",
                    "input": {"pattern": "{deep_denied.md,x"},
                }
            ],
            False,
        ),
        # Q6 round 9 L1: an unbalanced brace before a group is literal
        # text, and the group after it still expands
        (
            [
                {
                    "type": "tool_use",
                    "id": "g17",
                    "name": "Glob",
                    "input": {"pattern": "{,deep_{denied,y}.md"},
                }
            ],
            False,
        ),
        # Q6 round 9 L2: a whole denied stem with a wildcard in place of
        # the dot or the extension
        (
            [
                {
                    "type": "tool_use",
                    "id": "g18",
                    "name": "Glob",
                    "input": {"pattern": "**/deep_denied?md"},
                }
            ],
            False,
        ),
        (
            [
                {
                    "type": "tool_use",
                    "id": "g19",
                    "name": "Grep",
                    "input": {"pattern": "x", "glob": "deep_denied[.]md"},
                }
            ],
            False,
        ),
        (
            [
                {
                    "type": "tool_use",
                    "id": "g20",
                    "name": "Glob",
                    "input": {"pattern": "docs/**/deep_denied*"},
                }
            ],
            False,
        ),
        # broad patterns and wildcard fragments name nothing, and count
        (
            [
                {
                    "type": "tool_use",
                    "id": "g9",
                    "name": "Glob",
                    "input": {"pattern": "**/*"},
                },
                {
                    "type": "tool_use",
                    "id": "g10",
                    "name": "Glob",
                    "input": {"pattern": "**/*deep*"},
                },
                {
                    "type": "tool_use",
                    "id": "g11",
                    "name": "Grep",
                    "input": {"pattern": "x", "glob": "deep_denied_notes.md"},
                },
            ],
            True,
        ),
        # ordinary relative results inside the root, and a Grep regex that
        # mentions a denied file's name as text, count
        (
            [
                {
                    "type": "tool_use",
                    "id": "g5",
                    "name": "Grep",
                    "input": {"pattern": "gates.yaml", "path": "docs"},
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "g5",
                    "content": [
                        {"type": "text", "text": "docs/keep.md:1:gates.yaml"}
                    ],
                },
            ],
            True,
        ),
    ],
)
def test_claude_read_log_checks_patterns_and_relative_results(
    tmp_path, blocks, counts
):
    root = _invented_root(tmp_path)
    log = review_root.read_log(
        _claude_transcript(tmp_path, blocks),
        root,
        ["docs/denied.md", "gates.yaml", "docs/sub/deep_denied.md"],
    )
    assert log["review_counts"] is counts, log["paths_outside_root_or_denied"]


# Brace expansion and the pattern classifier (Q6 round 8 L1).

DENIED = ["docs/denied.md", "gates.yaml", "docs/sub/deep_denied.md"]
_plain = st.text(alphabet="xyz*?", max_size=4)


def test_brace_expansions_follow_glob_semantics():
    expand = review_root.brace_expansions
    assert expand("a{b,c}d") == ["abd", "acd"]
    assert expand("a{b,{c,d}}e") == ["abe", "ace", "ade"]
    assert expand("x{,y}") == ["x", "xy"]
    assert expand("{a,b}{c,d}") == ["ac", "ad", "bc", "bd"]
    # no comma at the group's own depth, or no closing brace: literal
    assert expand("{a}") == ["{a}"]
    assert expand("{a{b,c}}") == ["{ab}", "{ac}"]
    assert expand("{a,b") == ["{a,b"]
    # Q6 round 9 L1: the scan goes on after an unbalanced brace
    assert expand("{,a{b,c}d") == ["{,abd", "{,acd"]
    assert expand("a}{b,c}{d") == ["a}b{d", "a}c{d"]
    assert expand("plain/*.md") == ["plain/*.md"]
    with pytest.raises(OverflowError):
        expand("{a,b}" * 13)
    assert len(expand("{a,b}" * 12)) == review_root.BRACE_LIMIT
    assert review_root.pattern_kind("{a,b}" * 13, DENIED) == "unclassified"


@settings(max_examples=200, deadline=None)
@given(
    prefix=_plain,
    suffix=_plain,
    alternatives=st.lists(_plain, min_size=2, max_size=5),
)
def test_one_brace_group_expands_to_its_alternatives(
    prefix, suffix, alternatives
):
    pattern = prefix + "{" + ",".join(alternatives) + "}" + suffix
    assert review_root.brace_expansions(pattern) == [
        prefix + alternative + suffix for alternative in alternatives
    ]


@settings(max_examples=300, deadline=None)
@given(data=st.data())
def test_a_denied_name_split_across_a_brace_group_is_flagged(data):
    """Invariant: however a denied basename is cut into a brace group,
    under any directory prefix, the pattern is classed as denied."""
    name = data.draw(
        st.sampled_from([Path(d).name for d in DENIED])
        | st.just(Path(review_root.CODEBOOK_DIR).name)
    )
    start = data.draw(st.integers(0, len(name)))
    stop = data.draw(st.integers(start, len(name)))
    others = data.draw(st.lists(_plain, min_size=1, max_size=3))
    place = data.draw(st.integers(0, len(others)))
    group = [*others[:place], name[start:stop], *others[place:]]
    prefix = data.draw(st.sampled_from(["", "**/", "docs/", "*/x/"]))
    pattern = prefix + name[:start] + "{" + ",".join(group) + "}" + name[stop:]
    assert review_root.pattern_kind(pattern, DENIED) == "denied", pattern


@settings(max_examples=300, deadline=None)
@given(pattern=st.text(alphabet="xyz*?/{},", max_size=18))
@example("{/}x")
@example("{,{/}}x")
def test_a_pattern_naming_nothing_denied_stays_inside_the_root(pattern):
    """Invariant: a relative pattern with no dot and none of the denied
    names' letters is never flagged. It leaves the root exactly when bash
    or a glob engine expands it to an absolute alternative (ripgrep and
    Bun read ``{/}x`` as ``/x``)."""
    kind = review_root.pattern_kind(pattern, DENIED)
    absolute = any(
        text.startswith("/")
        for glob in (False, True)
        for text in review_root.brace_expansions(pattern, glob=glob)
    )
    assert kind == ("outside_root" if absolute else "inside_root"), pattern


@settings(max_examples=200, deadline=None)
@given(pattern=st.text(alphabet="ab./{},*", max_size=14))
def test_the_classifier_is_no_weaker_than_the_round_7_rule(pattern):
    """Differential: whatever the round-7 segment rule flagged on the
    pattern as written, the expanding classifier flags too. Since v7 a
    pattern it called denied may be classed as leaving the root instead,
    when an engine reads it as absolute (``{/ab}`` is ``/ab`` to
    ripgrep); either voids the review."""
    denied = ["a/b.a", "ab"]
    names = {"b.a", "ab", Path(review_root.CODEBOOK_DIR).name}
    stems = {"b"}
    pieces = pattern.replace("{", "/").replace("}", "/").replace(",", "/")
    old_denied = any(d in pattern for d in denied) or any(
        piece in names or any(piece.startswith(f"{s}.") for s in stems)
        for piece in pieces.split("/")
    )
    old_outside = pattern.startswith(("/", "~")) or ".." in pieces.split("/")
    kind = review_root.pattern_kind(pattern, denied)
    if old_outside:
        assert kind == "outside_root", pattern
    elif old_denied:
        assert kind in ("denied", "outside_root"), pattern


@settings(max_examples=300, deadline=None)
@given(data=st.data())
def test_a_whole_stem_with_a_wildcard_tail_is_flagged(data):
    """Invariant (Q6 round 9 L2): a segment holding a denied file's whole
    stem, with any of its extension's characters replaced by ``?`` or a
    one-character class, or the extension by ``*``, is classed as denied."""
    name = data.draw(st.sampled_from([Path(d).name for d in DENIED]))
    stem, extension = Path(name).stem, Path(name).suffix
    tail = data.draw(
        st.just("*")
        | st.tuples(
            *(st.sampled_from([char, "?", f"[{char}]"]) for char in extension)
        ).map("".join)
    )
    # A head that demands a character, such as ``?``, would not match the
    # name itself, so only an empty head or ``*`` belongs here.
    head = data.draw(st.sampled_from(["", "*"]))
    prefix = data.draw(st.sampled_from(["", "**/", "docs/", "*/x/"]))
    pattern = prefix + head + stem + tail
    assert review_root.pattern_kind(pattern, DENIED) == "denied", pattern


@settings(max_examples=200, deadline=None)
@given(
    junk=st.text(alphabet="{,", min_size=1, max_size=3),
    data=st.data(),
)
def test_literal_braces_do_not_hide_a_split_denied_name(junk, data):
    """Invariant (Q6 round 9 L1): unbalanced opening braces and commas
    before a group that splits a denied name do not stop it being read."""
    name = data.draw(st.sampled_from([Path(d).name for d in DENIED]))
    start = data.draw(st.integers(0, len(name)))
    stop = data.draw(st.integers(start, len(name)))
    pattern = (
        junk + name[:start] + "{" + name[start:stop] + ",y}" + name[stop:]
    )
    assert review_root.pattern_kind(pattern, DENIED) == "denied", pattern


# The v7 rule (after Q6 round 10): patterns read as glob engines read
# them, and every removed file denied.

#: An invented root record: three excluded files, one codebook file and
#: one other code-map table the builder removed.
RECORD = {
    "denied_paths": DENIED,
    "removed": [
        *DENIED,
        f"{review_root.CODEBOOK_DIR}/ry_invented_field_v1.json",
    ],
    "removed_codebook_tables": ["data/invented_code_map_table.md"],
}


def test_denied_from_record_takes_every_removed_file():
    assert review_root.denied_from_record(RECORD) == sorted(
        {
            *DENIED,
            f"{review_root.CODEBOOK_DIR}/ry_invented_field_v1.json",
            "data/invented_code_map_table.md",
        }
    )
    with pytest.raises(KeyError):
        review_root.denied_from_record({"denied_paths": DENIED})


@pytest.mark.parametrize(
    ("tool", "value", "counts"),
    [
        # Q6 round 10 L1: a class holding a comma or a brace
        ("Glob", "**/deep_denied[.,]md", False),
        ("Grep", "deep_denied[!,]md", False),
        ("Glob", "deep_denied[{.]md", False),
        # Q6 round 10 observation: a codebook file and a removed code-map
        # table named by basename, and the table's path
        ("Glob", "**/ry_invented_field_v1.json", False),
        ("Grep", "invented_code_map_table.md", False),
        ("Glob", "**/invented_code_map_table*", False),
        ("Read", "data/invented_code_map_table.md", False),
        # forms the engines read as the name (probed on invented files)
        ("Glob", "**/deep_{denied[.,]md,x}", False),
        ("Glob", "**/deep_{denied}.md", False),
        ("Grep", "deep_denied{.}md", False),
        ("Glob", "**/deep_denied\\.md", False),
        ("Glob", "**/deep_@(denied).md", False),
        ("Glob", "**/deep_denied[[:punct:]]md", False),
        ("Glob", "**/deep_denied[^,]md", False),
        ("Glob", "**/[d]eep_denied.md", False),
        ("Glob", "docs/sub[/x]deep_denied.md", False),
        # ripgrep lets a negated class stand for a slash
        ("Grep", "docs/sub[!x]deep_denied.md", False),
        # case: the root's file system ignores it
        ("Glob", "docs/sub/DEEP_DENIED.MD", False),
        ("Read", "GATES.YAML", False),
        ("Glob", "[gG]ates.yaml", False),
        # the #534 review's five: extglob repetition, Node's brace
        # sequences, Bun's escaped ] in a class, POSIX ascii and Node's
        # backslash separators; and a stem spelled by repetition
        ("Glob", "**/deep_denied+([.m])d", False),
        ("Glob", "**/deep_denied*([.m])d", False),
        ("Glob", "**/deep_denied[.,]{m..m}d", False),
        ("Glob", "**/deep_denied[.\\]]md", False),
        ("Glob", "**/deep_denied[[:ascii:]]md", False),
        ("Glob", "docs\\sub\\deep_denied.md", False),
        ("Glob", "**/d+(e)p_denied.md", False),
        # only ripgrep's brace reading (a class closed at \] and a group
        # without a comma) spells these, and only Bun's (a class that
        # escapes \] and holds the comma) spells the other
        ("Glob", "**/deep_{denied[.\\]m,zz]}{d}", False),
        ("Glob", "**/deep_d{enied[.\\],]md}", False),
        # #534 round 2: Bun reads [\\d] as d, which pins the stem
        ("Glob", "**/[\\d]eep_denied.md", False),
        ("Grep", "deep_d[\\e]nied.md", False),
        # a file name holds no /, so ripgrep's [d/] pins the stem
        ("Glob", "**/[d/]eep_denied.md", False),
        # #534 round 3: nor a NUL, so Node's and Bun's [d\0] pins it
        ("Glob", "**/[d\x00]eep_denied.md", False),
        ("Grep", "d[e\x00]ep_denied.md", False),
        # 64 classes that may be / give 2,145 segments, under the limit
        ("Glob", "[a/]" * 64 + "deep_denied.md", False),
        # a filter that excludes a denied name names it (conservative)
        ("Glob", "**/deep_denied!(.md)", False),
        # nested too deep to read: unclassified, so void
        ("Glob", "@(x)" * 1100, False),
        # broad patterns and wildcard fragments name nothing, and count
        ("Glob", "**/*", True),
        ("Glob", "**/*deep*", True),
        ("Grep", "deep_denied_notes.md", True),
        ("Glob", "**/*b0_1*", True),
        ("Glob", "_review_context/**", True),
        ("Glob", "*.{py,json}", True),
        ("Glob", "{tier_counts.json,README-tiers.md}", True),
        ("Glob", "track_b_b0_1_addendum_q6_readlog_r[567].json", True),
        # the disclosed limit: a wildcard standing for part of a stem
        ("Glob", "?ates.yaml", True),
        ("Glob", "[gx]ates.yaml", True),
        # an extglob alternative, like a brace alternative, spells it
        ("Glob", "g*(a|x)tes.yaml", False),
    ],
)
def test_read_log_v7_cases(tmp_path, tool, value, counts):
    root = _invented_root(tmp_path)
    given = {
        "Glob": {"pattern": value},
        "Grep": {"pattern": "x", "glob": value},
        "Read": {"file_path": str(root / value)},
    }[tool]
    blocks = [{"type": "tool_use", "id": "v", "name": tool, "input": given}]
    log = review_root.read_log(
        _claude_transcript(tmp_path, blocks),
        root,
        review_root.denied_from_record(RECORD),
    )
    assert log["schema"] == "track_b_b0_1_review_read_log.v7"
    assert log["n_denied"] == 5
    assert log["review_counts"] is counts, log["paths"]


@pytest.mark.parametrize(
    "pattern",
    [
        # #534 round 1: nested too deep to read
        "@(x)" * 1100,
        # #534 round 2: a sequence number too long to read, and a chain of
        # empty extglobs whose automaton passes CLOSURE_LIMIT
        "{" + "1" * 4500 + "..1}",
        "+()" * 900 + "deep_denied.md",
        # longer than PATTERN_LIMIT, and too many segments to read:
        # 90 classes that may be / give 91 * 92 / 2 = 4,186
        "x" * (review_root.PATTERN_LIMIT + 1),
        "[a/]" * 90 + "deep_denied.md",
        # #534 round 3: a class past CLASS_LIMIT, and work charged while
        # braces expand behind 100 unmatched openers
        "[ -\U0010ffff]eep_denied.md",
        "{" * 100 + "{a,b}" * 12 + "deep_denied.md",
        "[" * 100 + "{a,b}" * 12 + "deep_denied.md",
    ],
)
def test_patterns_too_large_to_read_are_unclassified(pattern):
    assert review_root.pattern_kind(pattern, DENIED) == "unclassified"


def test_each_work_limit_holds_below_the_length_limit():
    """Every limit gives unclassified on a pattern short enough to pass
    PATTERN_LIMIT: the closure budget, the work budget, recursion depth
    and a sequence number too long for int(). Each call leaves no work
    budget running and no memo table filled."""
    kind = review_root.pattern_kind
    assert kind("+()" * 300 + "deep_denied.md", DENIED) == "unclassified"
    product = "{" * 100 + "{a,b}" * 12 + "deep_denied.md" + "}" * 100
    assert kind(product, DENIED) == "unclassified"
    assert review_root._WORK.left is None
    assert review_root._automaton.cache_info().currsize == 0
    assert review_root.class_end.cache_info().currsize == 0
    nested = "@(" * 150 + "x" + ")" * 150
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(len(inspect.stack()) + 60)
    try:
        assert kind(nested, DENIED) == "unclassified"
    finally:
        sys.setrecursionlimit(limit)
    digits = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(640)
    try:
        assert kind("{" + "1" * 700 + "..1}", DENIED) == "unclassified"
    finally:
        sys.set_int_max_str_digits(digits)
    assert len(nested) < review_root.PATTERN_LIMIT


def test_unbalanced_openers_up_to_the_limit_are_still_read():
    """Unclosed braces, extglobs and classes at the length limit are read
    to the end (each class end is found once), and a denied name after
    them is still seen."""
    filler = "{@(["
    pattern = filler * ((review_root.PATTERN_LIMIT - 20) // len(filler))
    assert review_root.pattern_kind(pattern, DENIED) == "inside_root"
    assert (
        review_root.pattern_kind(pattern + "/deep_denied.md", DENIED)
        == "denied"
    )


def test_readlog_cli_denies_every_file_the_root_record_removed(tmp_path):
    root = _invented_root(tmp_path)
    record = tmp_path / "root-record.json"
    record.write_text(json.dumps(RECORD), encoding="utf-8")
    transcript = _claude_transcript(
        tmp_path,
        [
            {
                "type": "tool_use",
                "id": "c",
                "name": "Glob",
                "input": {"pattern": "**/invented_code_map_table.md"},
            }
        ],
    )
    out = tmp_path / "log.json"
    argv = ["readlog", "--transcript", str(transcript), "--root", str(root)]
    argv += ["--root-record", str(record), "--record", str(out)]
    assert review_root.main(argv) == 0
    log = json.loads(out.read_text(encoding="utf-8"))
    assert log["n_denied"] == 5
    assert log["review_counts"] is False
    assert log["paths"] == {"pattern:**/invented_code_map_table.md": "denied"}


def test_glob_readings_follow_the_engines():
    expand = review_root.brace_expansions
    # bash and Node: a group with no comma is literal, and a comma inside
    # a class splits
    assert expand("a{b}c") == ["a{b}c"]
    assert expand("{a[.,]b,c}") == ["a[.", "]b", "c"]
    # ripgrep and Bun: a group with no comma is its content; a class and
    # an escape are one token
    assert expand("a{b}c", glob=True) == ["abc"]
    assert expand("x{}y", glob=True) == ["xy"]
    assert expand("{{i}}", glob=True) == ["i"]
    assert expand("{a[.,]b,c}", glob=True) == ["a[.,]b", "c"]
    assert expand("a\\{b,c}", glob=True) == ["a\\{b,c}"]
    assert expand("{,a{b,c}d", glob=True) == ["{,abd", "{,acd"]
    extglob = review_root.extglob_expansions
    assert extglob("a@(b|c)d") == ["abd", "acd"]
    assert extglob("+(b)") == ["b"]
    assert extglob("?(b)x") == ["x", "bx"]
    assert extglob("*(b|c)") == ["", "b", "c"]
    assert extglob("!(b)x") == ["*x"]
    assert extglob("@(a|@(b|c))") == ["a", "b", "c"]
    assert extglob("@(a") == ["@(a"]
    assert extglob("a[@(]b|c)") == ["a[@(]b|c)"]
    assert extglob("\\@(a)") == ["\\@(a)"]
    tokens = review_root.glob_tokens
    assert tokens("a[.,]b") == (
        ("lit", "a"),
        ("set", frozenset(".,")),
        ("lit", "b"),
    )
    assert tokens("[!x][^x]") == (("notset", frozenset("x")),) * 2
    assert tokens("[]a][a-c][[:digit:]]") == (
        ("set", frozenset("]a")),
        ("set", frozenset("abc")),
        ("set", frozenset("0123456789")),
    )
    assert tokens("[g]\\.{,}*?") == (
        ("lit", "g"),
        ("lit", "."),
        ("cut", "{"),
        ("cut", ","),
        ("cut", "}"),
        ("star", ""),
        ("any", ""),
    )
    assert tokens("[Gg]X", fold=True) == (("lit", "g"), ("lit", "x"))
    assert tokens("[a") == (("lit", "["), ("lit", "a"))
    with pytest.raises(OverflowError):
        extglob("@(a|b)" * 13)
    # bash and Node's sequences, only when asked for
    assert expand("a{1..3}b") == ["a{1..3}b"]
    assert expand("a{1..3}b", sequences=True) == ["a1b", "a2b", "a3b"]
    assert expand("{c..a}", sequences=True) == ["c", "b", "a"]
    assert expand("{1..5..2}", sequences=True) == ["1", "3", "5"]
    # a zero-padded end pads every item to the longer end's width
    assert expand("{08..10}", sequences=True) == ["08", "09", "10"]
    assert expand("{-05..5..5}", sequences=True) == ["-05", "000", "005"]
    assert expand("{a..1}", sequences=True) == ["{a..1}"]
    with pytest.raises(OverflowError):
        expand("{1..99999}", sequences=True)
    # Bun: a backslash inside a class escapes the next character, so
    # [\\d] is d alone; ripgrep reads it as a backslash or d
    assert tokens("[\\d]") == (("set", frozenset("\\d")),)
    assert tokens("[\\d]", escapes=True) == (("lit", "d"),)
    assert review_root.class_end("[.\\]]", 0) == 3
    assert review_root.class_end("[.\\]]", 0, escapes=True) == 4
    assert expand("{a[.\\],]b,c}", glob=True, escapes=True) == [
        "a[.\\],]b",
        "c",
    ]
    # an extglob is one token, read exactly
    assert tokens("a+(b|[cd])") == (
        ("lit", "a"),
        ("group", ("+", ((("lit", "b"),), (("set", frozenset("cd")),)))),
    )
    assert tokens("[[:ascii:]][[:nonesuch:]]")[0] == (
        "set",
        frozenset(map(chr, range(128))),
    )
    assert len(tokens("[[:nonesuch:]]")[0][1]) == 95
    assert review_root.pattern_kind("@(a|b)" * 13, DENIED) == "unclassified"


#: Pattern pieces whose fnmatch reading is the engines' reading.
_PIECES = ["a", "b", ".", "*", "?", "[ab]", "[.a]", "[!a]", "[a-b]", "[]a]"]


@settings(max_examples=400, deadline=None)
@given(
    pieces=st.lists(st.sampled_from(_PIECES), max_size=6),
    name=st.text(alphabet="ab.]", max_size=6),
)
def test_glob_match_agrees_with_fnmatch_where_they_share_syntax(pieces, name):
    """Differential: on syntax fnmatch and the engines read alike, the
    token matcher and ``fnmatchcase`` agree."""
    pattern = "".join(pieces)
    assert review_root.glob_match(
        name, review_root.glob_tokens(pattern)
    ) is fnmatchcase(name, pattern), (pattern, name)


@settings(max_examples=300, deadline=None)
@given(text=st.text(alphabet="ab./{},*?", max_size=16))
def test_class_free_segments_are_the_plain_cut(text):
    """Without classes or escapes, the engines' segments are the v6 cut
    at every slash, brace and comma."""
    views = [
        "".join(v if k in ("lit", "cut") else "\0" for k, v in segment)
        for segment in review_root.glob_segments(review_root.glob_tokens(text))
    ]
    plain = re.split(r"[/{},]", text.replace("*", "\0").replace("?", "\0"))
    assert views == plain, text


def _draw_extension_classes(data, extension, members, negated):
    """The extension with at least one character replaced by a class."""
    replace = data.draw(
        st.lists(
            st.booleans(), min_size=len(extension), max_size=len(extension)
        ).filter(any)
    )
    out = []
    for char, swap in zip(extension, replace, strict=True):
        if not swap:
            out.append(char)
            continue
        extra = data.draw(st.lists(st.sampled_from(members), unique=True))
        if negated and data.draw(st.booleans()):
            # A negated class of characters that are not the true one.
            others = [c for c in extra if c != char] or [","]
            out.append("[" + data.draw(st.sampled_from("!^")))
            out.append("".join(data.draw(st.permutations(others))) + "]")
            continue
        body = data.draw(st.permutations([char, *extra]))
        out.append("[" + "".join(body) + "]")
    return "".join(out)


@settings(max_examples=400, deadline=None)
@given(data=st.data())
def test_a_class_holding_a_comma_or_brace_still_names_the_file(data):
    """Invariant (Q6 round 10 L1): a denied basename whose extension
    characters are replaced by bracket classes that hold the true
    character and any of ``,``, ``{`` and ``}`` is classed as denied, as
    are negated classes of those three (``stem[!,]md``)."""
    name = data.draw(st.sampled_from([Path(d).name for d in DENIED]))
    stem, extension = Path(name).stem, Path(name).suffix
    tail = _draw_extension_classes(data, extension, ",{}", negated=True)
    head = data.draw(st.sampled_from(["", "*"]))
    prefix = data.draw(st.sampled_from(["", "**/", "docs/", "*/x/"]))
    pattern = prefix + head + stem + tail
    assert review_root.pattern_kind(pattern, DENIED) == "denied", pattern


@settings(max_examples=300, deadline=None)
@given(data=st.data())
def test_engine_spellings_of_a_denied_name_are_flagged(data):
    """Invariant: a denied basename spelled with engine syntax alone is
    classed as denied, however its letters are cased, escaped, wrapped in
    a brace group without a comma, or wrapped in an extglob."""
    name = data.draw(
        st.sampled_from([Path(d).name for d in RECORD["removed"]])
        | st.sampled_from(RECORD["removed_codebook_tables"]).map(
            lambda p: Path(p).name
        )
    )
    chars = []
    for char in name:
        cased = data.draw(st.sampled_from([char, char.upper()]))
        chars.append(data.draw(st.sampled_from([cased, "\\" + cased])))
    start = data.draw(st.integers(0, len(chars)))
    stop = data.draw(st.integers(start, len(chars)))
    opener, closer = data.draw(
        st.sampled_from(
            [("{", "}"), ("{{", "}}"), ("@(", ")"), ("+(", ")"), ("", "")]
        )
    )
    spelled = (
        "".join(chars[:start])
        + opener
        + "".join(chars[start:stop])
        + closer
        + "".join(chars[stop:])
    )
    prefix = data.draw(st.sampled_from(["", "**/", "docs/sub/"]))
    pattern = prefix + spelled
    # Node reads a backslash as a slash, so an escape at the start of a
    # segment can also read as leaving the root; either voids the review.
    assert review_root.pattern_kind(
        pattern, review_root.denied_from_record(RECORD)
    ) in ("denied", "outside_root"), pattern


#: Extglob-bearing pieces and the regular expression each stands for.
_GROUP_PIECES = {
    "a": "a",
    "b": "b",
    "A": "A",
    ".": r"\.",
    "*": "[^/]*",
    "?": "[^/]",
    "[ab]": "[ab]",
    "[aA]": "[aA]",
    "[!a]": "[^/a]",
    "@(a|b)": "(?:a|b)",
    "+(a)": "(?:a)+",
    "*(b)": "(?:b)*",
    "?(a)": "(?:a)?",
    "+([ab])": "(?:[ab])+",
    "[a/]": "[a/]",
    "@(a|+(b))": "(?:a|(?:b)+)",
    "!(a)": "[^/]*",
}


@settings(max_examples=500, deadline=None)
@given(
    pieces=st.lists(st.sampled_from(sorted(_GROUP_PIECES)), max_size=5),
    name=st.text(alphabet="abAB.", max_size=6),
)
def test_the_automaton_matches_as_a_regular_expression(pieces, name):
    """Differential: the automaton reads extglob repetition exactly, as a
    regular expression does (``!(...)`` read as ``*`` in both)."""
    pattern = "".join(pieces)
    expected = "".join(_GROUP_PIECES[piece] for piece in pieces)
    assert review_root.glob_match(
        name, review_root.glob_tokens(pattern)
    ) is bool(re.fullmatch(expected, name)), (pattern, name)


@settings(max_examples=500, deadline=None)
@given(
    pieces=st.lists(st.sampled_from(sorted(_GROUP_PIECES)), max_size=5),
    name=st.text(alphabet="abAB.", min_size=1, max_size=6),
)
# a class of one letter's two cases pins it, case aside
@example(pieces=["[aA]", "b"], name="ab")
def test_pins_stem_is_the_brute_force_rule(pieces, name):
    """Differential: ``pins_stem`` holds exactly when the segment matches
    the name and no name differing at one stem position, other than in
    case, also matches. ``\\x01`` stands for every character no piece
    names."""
    tokens = review_root.glob_tokens("".join(pieces))
    match = review_root.glob_match
    stem = len(Path(name).stem)
    brute = match(name, tokens) and not any(
        match(name[:i] + other + name[i + 1 :], tokens)
        for i in range(stem)
        for other in "abAB.\x01"
        if other.casefold() != name[i].casefold()
    )
    assert review_root.pins_stem(name, tokens) is brute, (pieces, name)


# The v6 classifier, frozen as it stood at round 10, for the differential
# test below.


def _v6_brace_expansions(pattern, limit=review_root.BRACE_LIMIT):
    start = pattern.find("{")
    while start != -1:
        depth = 0
        commas = []
        end = -1
        for index in range(start, len(pattern)):
            char = pattern[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index
                    break
            elif char == "," and depth == 1:
                commas.append(index)
        if end != -1 and commas:
            out = []
            for left, right in pairwise([start, *commas, end]):
                out.extend(
                    _v6_brace_expansions(
                        pattern[:start]
                        + pattern[left + 1 : right]
                        + pattern[end + 1 :],
                        limit,
                    )
                )
                if len(out) > limit:
                    raise OverflowError
            return out
        start = pattern.find("{", start + 1)
    return [pattern]


def _v6_pattern_kind(pattern, denied):
    codebook = review_root.CODEBOOK_DIR
    names = {Path(d).name for d in denied} | {Path(codebook).name}
    stems = {Path(d).stem for d in denied if Path(d).suffix}
    try:
        alternatives = _v6_brace_expansions(pattern)
    except OverflowError:
        return "unclassified"
    kinds = set()
    for text in {pattern, *alternatives}:
        segments = re.split(r"[/{},]", text)
        if text.startswith(("/", "~")) or ".." in segments:
            kinds.add("outside_root")
        if any(d in text for d in denied) or codebook in text:
            kinds.add("denied")
        for segment in segments:
            if segment in names or any(
                segment.startswith(f"{stem}.") for stem in stems
            ):
                kinds.add("denied")
            if any(
                Path(name).stem in segment and fnmatchcase(name, segment)
                for name in names
            ):
                kinds.add("denied")
    for kind in ("outside_root", "denied"):
        if kind in kinds:
            return kind
    return "inside_root"


#: Glob syntax the mixed strategy splices into a denied name.
_SYNTAX = ["[", "]", "{", "}", ",", "!", "^", "*", "?", "/", "\\", "@(", ")"]


@st.composite
def _mixed(draw):
    """A denied name, or plain letters, with glob syntax spliced in."""
    base = draw(
        st.sampled_from([Path(d).name for d in DENIED])
        | st.text(alphabet="ab.", max_size=6)
    )
    pieces = list(base)
    for _ in range(draw(st.integers(0, 4))):
        at = draw(st.integers(0, len(pieces)))
        pieces.insert(at, draw(st.sampled_from(_SYNTAX)))
    prefix = draw(st.sampled_from(["", "**/", "docs/", "/", "../"]))
    return prefix + "".join(pieces)


@settings(max_examples=600, deadline=None)
@given(pattern=_mixed() | st.text(alphabet="ab./{},*[]!^\\", max_size=14))
# v6 cut inside the class and saw ``deep_denied.md]``; the engines read one
# character. v7 keeps v6's cut, so it still voids this.
@example("[,deep_denied.md]")
def test_v7_voids_whatever_v6_voided(pattern):
    """Differential: every pattern the round-10 rule (v6) did not class as
    inside the root, v7 does not either."""
    if _v6_pattern_kind(pattern, DENIED) != "inside_root":
        assert review_root.pattern_kind(pattern, DENIED) != "inside_root"


@settings(max_examples=600, deadline=None)
@given(pattern=_mixed())
# fnmatch reads ``[^.,]`` as a class holding ``^``, ``.`` and ``,``; the
# engines read it as negated, so only the smallest fix catches this one.
@example("deep_{denied[^.,]md,x}")
def test_v7_catches_what_round_10_s_smallest_fix_would(pattern):
    """Differential: round 10's smallest fix ran the whole-stem test on
    each alternative's ``/``-segments, uncut at commas or braces. Every
    pattern it would flag, v7 flags."""
    names = {Path(d).name for d in DENIED}
    try:
        alternatives = {
            pattern,
            *review_root.brace_expansions(pattern),
            *review_root.brace_expansions(pattern, glob=True),
        }
    except OverflowError:
        return
    flagged = any(
        Path(name).stem in segment and fnmatchcase(name, segment)
        for text in alternatives
        for segment in text.split("/")
        for name in names
    )
    if flagged:
        assert review_root.pattern_kind(pattern, DENIED) != "inside_root"


# Differential against the glob engines themselves, on invented files.

_NODE_PROBE = """
const fs = require("node:fs");
const [cwd, list] = process.argv.slice(2);
const out = {};
for (const p of JSON.parse(fs.readFileSync(list, "utf8"))) {
  try { out[p] = fs.globSync(p, { cwd }); } catch (e) { out[p] = []; }
}
console.log(JSON.stringify(out));
"""
_BUN_PROBE = """
const fs = require("node:fs");
const [cwd, list] = process.argv.slice(2);
const out = {};
for (const p of JSON.parse(fs.readFileSync(list, "utf8"))) {
  try { out[p] = [...new Bun.Glob(p).scanSync({ cwd })]; }
  catch (e) { out[p] = []; }
}
console.log(JSON.stringify(out));
"""


def _engine_available(engine):
    if engine == "node":
        if shutil.which("node") is None:
            return False
        probe = "process.exit(require('node:fs').globSync ? 0 : 1)"
        return subprocess.run(["node", "-e", probe]).returncode == 0
    return shutil.which(engine) is not None


def _engine_matches(engine, root, patterns, tmp_path):
    """Which invented files each pattern matches under ``engine``."""
    if engine == "rg":
        out = {}
        for pattern in patterns:
            if "\x00" in pattern:
                # A command line cannot hold a NUL.
                out[pattern] = []
                continue
            listed = subprocess.run(
                ["rg", "--files", "--no-ignore", "-g", pattern, "."],
                cwd=root,
                capture_output=True,
                text=True,
            ).stdout
            out[pattern] = [
                line.removeprefix("./") for line in listed.splitlines()
            ]
        return out
    tmp_path.mkdir(exist_ok=True)
    listing = tmp_path / "patterns.json"
    listing.write_text(json.dumps(patterns), encoding="utf-8")
    script = tmp_path / f"probe_{engine}.js"
    probe = _NODE_PROBE if engine == "node" else _BUN_PROBE
    script.write_text(probe, encoding="utf-8")
    result = subprocess.run(
        [engine, str(script), str(root), str(listing)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _spellings(seed, count):
    """Patterns that spell a denied name with engine syntax alone.

    Each pattern applies one to three changes to the name: escape a
    character, flip its case, put it in a one-character class or a
    two-case class, put an extension character in a class with other
    characters (or a POSIX, negated or escaped-bracket class), put any
    character in Bun's escaped class, ripgrep's ``[c/]`` or a class with
    a NUL, wrap a run
    in a brace group or an extglob, spell a doubled letter by repetition
    (``+(e)``) or a letter by a one-item sequence (``{e..e}``), or read
    two extension characters by a repeated class. The path may be
    written with Node's backslashes. None puts a wildcard in place of a
    stem character, so every engine match spells the name.
    """
    rng = random.Random(seed)
    extras = [",", "{", "}", "/", "x", "-", "!", "^", "]", "["]
    wraps = ["{%s}", "{%s,}", "{,%s}", "{%s,zz}", "{{%s}}"]
    wraps += ["@(%s)", "+(%s)", "?(%s)", "*(%s)", "@(%s|zz)"]
    out = []
    for _ in range(count):
        name = rng.choice([Path(d).name for d in DENIED])
        cut = len(Path(name).stem)
        units = list(name)
        for _ in range(rng.randint(1, 3)):
            change = rng.choice(
                ["escape", "case", "one", "cases", "class", "class", "wrap"]
                + ["repeat", "sequence", "escaped-class", "escaped-one"]
            )
            index = rng.randrange(len(units))
            char = units[index]
            following = units[index + 1] if index + 1 < len(units) else ""
            if change == "repeat" and len(char) == 1 and char == following:
                # a doubled letter spelled by repetition: ee as +(e)
                units[index : index + 2] = [f"+({char})"]
            elif change == "repeat" and index >= cut and len(following) == 1:
                # two extension characters read by a repeated class
                units[index : index + 2] = [f"+([{char}{following}])"]
            elif change == "sequence" and char.isalpha() and len(char) == 1:
                if index < cut:
                    units[index] = f"{{{char}..{char}}}"
                else:
                    low, high = chr(ord(char) - 1), chr(ord(char) + 1)
                    units[index] = f"{{{low}..{high}}}"
            elif change == "escaped-one" and len(char) == 1:
                # Bun reads [\\c] as c alone; in a file name ripgrep's
                # [c/] can only be c
                units[index] = rng.choice(
                    [f"[\\{char}]", f"[{char}/]", f"[{char}\x00]"]
                )
            elif change == "escaped-class" and index >= cut:
                units[index] = rng.choice(
                    [f"[{char}\\]]", "[[:ascii:]]", f"[\\]{char}]"]
                )
            elif change in (
                "repeat",
                "sequence",
                "escaped-class",
                "escaped-one",
            ):
                continue
            elif change == "wrap" or len(char) != 1:
                stop = rng.randint(index + 1, len(units))
                inner = "".join(units[index:stop])
                units[index:stop] = [rng.choice(wraps) % inner]
            elif change == "escape":
                units[index] = "\\" + char
            elif change == "case":
                units[index] = char.swapcase()
            elif change == "one":
                units[index] = f"[{char}]"
            elif change == "cases":
                units[index] = f"[{char}{char.swapcase()}]"
            elif index >= cut:
                members = [char, *rng.sample(extras, rng.randint(1, 2))]
                rng.shuffle(members)
                units[index] = rng.choice(
                    [
                        "[" + "".join(members) + "]",
                        "[[:punct:]]" if char == "." else "[[:alpha:]]",
                        "[!,{}]",
                        "[^/,]",
                    ]
                )
        prefix = rng.choice(
            ["", "**/", "docs/sub/", "docs/**/", "docs\\sub\\"]
        )
        out.append(prefix + "".join(units))
    return sorted(set(out))


@pytest.mark.parametrize("engine", ["rg", "node", "bun"])
def test_every_engine_match_of_a_spelled_denied_name_is_flagged(
    tmp_path, engine
):
    """Differential: wherever ripgrep, Node or Bun finds a denied file
    through a pattern that spells its name with syntax alone, the
    classifier flags the pattern. Which engine the lanes' Glob and Grep
    tools use is not assumed, so all three are checked."""
    if not _engine_available(engine):
        pytest.skip(f"{engine} is not installed")
    root = _invented_root(tmp_path)
    (root / "docs/sub").mkdir(parents=True)
    (root / "docs/sub/deep_denied.md").write_text("x", encoding="utf-8")
    (root / "docs/sub/deep_x.md").write_text("x", encoding="utf-8")
    patterns = _spellings(seed=20261012, count=1000)
    matches = _engine_matches(engine, root, patterns, tmp_path / "probe")
    denied = {d.casefold() for d in DENIED}
    hits = [
        pattern
        for pattern in patterns
        if any(path.casefold() in denied for path in matches[pattern])
    ]
    # The corpus must exercise the engine, or the test proves nothing.
    assert len(hits) >= 100, (engine, len(hits))
    missed = [
        pattern
        for pattern in hits
        if review_root.pattern_kind(pattern, DENIED) == "inside_root"
    ]
    assert missed == [], missed[:20]
