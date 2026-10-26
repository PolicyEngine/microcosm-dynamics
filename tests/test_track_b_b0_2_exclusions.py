"""B0.2's files stay out of every blinded review root.

The dynamics coordinator separated B0.2 from the B2 successor design on
2026-10-21: successor-design roles may not read B0.2's work. B0.2's
structural counts must be on an exclusion inventory before they reach
master. ``docs/design/track_b_b0_2_exclusions.json`` is that inventory, a
standing record that ``scripts/track_b_b0_1_review_root.py`` applies to
every build, whatever inventories the build names.

The record lists two files before they exist: the counts the frozen
protocol writes, and B0.2's exposure inventory. Every other B0.2 file in
the repository must be listed, so a new one cannot reach master unlisted:
a file named as B0.2's, or any file in a folder so named, such as the
evidence folder (review round 4 found its files left in review roots).
Both the rule and the exclusions read full paths, so a file elsewhere
that shares a basename with one of B0.2's is neither listed nor removed.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_review_root as review_root  # noqa: E402

RECORD_PATH = "docs/design/track_b_b0_2_exclusions.json"
RECORD = ROOT / RECORD_PATH
#: Listed ahead of their arrival.
NOT_YET_COMMITTED = {
    "docs/design/track_b_b0_2_counts.json",
    "docs/design/track_b_b0_2_exposure_inventory.json",
}
B0_2_FILES = NOT_YET_COMMITTED | {
    "docs/design/track_b_b0_2_counts_mutations.json",
    "docs/design/track_b_b0_2_counts_report.txt",
    "docs/design/track_b_b0_2_evidence/calibrate.py",
    "docs/design/track_b_b0_2_evidence/calibration.txt",
    "docs/design/track_b_b0_2_evidence/exhaust_closure.py",
    "docs/design/track_b_b0_2_evidence/exhaust_closure.txt",
    "docs/design/track_b_b0_2_evidence/invented_panel.py",
    "docs/design/track_b_b0_2_evidence/mutation_specs.json",
    "docs/design/track_b_b0_2_evidence/mutations.py",
    "docs/design/track_b_b0_2_evidence/oracle.py",
    "docs/design/track_b_b0_2_evidence/ranges.py",
    "docs/design/track_b_b0_2_evidence/ranges.txt",
    "docs/design/track_b_b0_2_evidence/search.py",
    "docs/design/track_b_b0_2_evidence/search.txt",
    "docs/design/track_b_b0_2_evidence/singleton.py",
    "docs/design/track_b_b0_2_evidence/singleton.txt",
    "docs/design/track_b_b0_2_landscape.md",
    "docs/design/track_b_b0_2_plan.md",
    "docs/design/track_b_b0_2_protocol.md",
    "scripts/track_b_b0_2_counts.py",
    "tests/test_track_b_b0_2_counts.py",
}
#: Name B0.2's files without holding any of their content.
NOT_EXCLUDED = {RECORD_PATH, "tests/test_track_b_b0_2_exclusions.py"}
#: Files outside B0.2 that share a basename with one of its files. They
#: are matched on their full paths, so each stays in a root.
DECOYS = {
    "docs/other/calibrate.py",
    "docs/design/calibration.txt",
    "scripts/oracle.py",
    "tests/evidence/mutation_specs.json",
    "docs/design/track_b_b0_1_evidence/search.txt",
}


def b0_2_named(path: str) -> bool:
    """Whether a repository path is named as one of B0.2's files: its own
    name, or the name of any folder it is in."""
    *folders, name = path.split("/")
    return name.startswith(("track_b_b0_2_", "test_track_b_b0_2_")) or any(
        folder.startswith("track_b_b0_2_") for folder in folders
    )


def record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_the_standing_record_lists_b0_2s_files():
    entries = record()["q6_exclusions"]
    assert record()["schema"] == "track_b_b0_2_exclusions.v1"
    paths = [entry["path"] for entry in entries]
    assert paths == sorted(B0_2_FILES)
    assert all(entry["scope"] == "whole_file" for entry in entries)
    assert all(entry["lines"] is None for entry in entries)
    assert RECORD_PATH in review_root.STANDING_EXCLUSIONS
    denied = set(review_root.denied_paths(review_root.standing_inventories()))
    assert B0_2_FILES <= denied


def test_every_b0_2_file_in_the_repository_is_listed():
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode()
    named = {path for path in tracked.split("\0") if b0_2_named(path)}
    assert named - NOT_EXCLUDED <= B0_2_FILES
    for relative in B0_2_FILES - NOT_YET_COMMITTED:
        assert relative in named, relative


def test_the_name_rule_catches_b0_2s_files_only():
    assert b0_2_named("docs/design/track_b_b0_2_counts.json")
    assert b0_2_named("tests/test_track_b_b0_2_new.py")
    assert b0_2_named("track_b_b0_2_top.md")
    assert b0_2_named("docs/design/track_b_b0_2_evidence/calibrate.py")
    assert b0_2_named("docs/design/track_b_b0_2_evidence/deeper/new.txt")
    assert not b0_2_named("docs/design/track_b_b0_1_counts.json")
    assert not b0_2_named("docs/design/track_b_b0_2x/plain.md")
    assert not b0_2_named("scripts/old_track_b_b0_2_counts.py")
    # The rule reads the full path: a basename shared with an evidence file
    # is not B0.2's outside a B0.2 folder.
    for decoy in DECOYS:
        assert not b0_2_named(decoy), decoy
        name = decoy.rsplit("/", 1)[1]
        assert any(path.endswith(f"/{name}") for path in B0_2_FILES), decoy


def test_build_removes_b0_2s_files_without_any_inventory(
    tmp_path, monkeypatch
):
    files = {relative: "invented" for relative in B0_2_FILES}
    files["docs/keep.md"] = "kept text"
    files[RECORD_PATH] = "{}"
    files.update({decoy: "decoy text" for decoy in DECOYS})

    def run(command, cwd=None, check=False):
        archive = Path(command[command.index("-o") + 1])
        with tarfile.open(archive, "w") as tar:
            for relative, content in files.items():
                data = content.encode()
                info = tarfile.TarInfo(relative)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

    monkeypatch.setattr(review_root, "subprocess", SimpleNamespace(run=run))
    out = tmp_path / "root"
    built = review_root.build("h", out, [], {})
    assert B0_2_FILES <= set(built["removed"])
    for relative in B0_2_FILES:
        assert not (out / relative).exists(), relative
    # Exclusion is by full path: every decoy sharing a basename with an
    # excluded file is kept, with its content.
    assert set(review_root.manifest(out)) == {
        "docs/keep.md",
        RECORD_PATH,
        *DECOYS,
    }
    for decoy in DECOYS:
        assert (out / decoy).read_text() == "decoy text", decoy
