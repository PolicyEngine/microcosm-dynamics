"""Tests for the Q6 review-root builder and read log, on invented files.

No repository file on the exclusion list is opened: the pieces are
exercised on a temporary directory with invented content.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
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
def test_a_pattern_naming_nothing_denied_stays_inside_the_root(pattern):
    """Invariant: a relative pattern with no dot and none of the denied
    names' letters is never flagged."""
    kind = review_root.pattern_kind(pattern, DENIED)
    absolute = any(
        text.startswith("/") for text in review_root.brace_expansions(pattern)
    )
    assert kind == ("outside_root" if absolute else "inside_root"), pattern


@settings(max_examples=200, deadline=None)
@given(pattern=st.text(alphabet="ab./{},*", max_size=14))
def test_the_classifier_is_no_weaker_than_the_round_7_rule(pattern):
    """Differential: whatever the round-7 segment rule flagged on the
    pattern as written, the expanding classifier flags too."""
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
        assert kind == "denied", pattern


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
