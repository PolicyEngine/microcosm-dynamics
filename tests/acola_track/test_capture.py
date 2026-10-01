"""The approved table and its note are isolated from invented page text."""

import importlib.util
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "acola_capture", ROOT / "scripts/capture_tr2026_v_c1.py"
)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


@given(st.text(alphabet="abc XYZé—\n", max_size=100))
@settings(deadline=None)
def test_fragment_keeps_exact_bytes_and_excludes_other_table_text(prefix):
    fragment = (
        '<table class="approved"><caption>'
        + capture.CAPTION
        + "</caption><tr><td>Invented</td></tr></table>"
    ).encode()
    before = (prefix + "<table><caption>Other</caption></table>").encode()
    after = b"<table><caption>Other</caption><tr><td>hidden</td></tr></table>"
    result, start, end = capture.table_fragment(before + fragment + after)
    assert result == fragment
    assert start == len(before)
    assert end == len(before) + len(fragment)


@pytest.mark.parametrize("count", [0, 2])
def test_caption_must_match_exactly_once(count):
    fragment = (
        "<table><caption>" + capture.CAPTION + "</caption></table>"
    ).encode()
    with pytest.raises(ValueError, match="exactly one table"):
        capture.table_fragment(fragment * count)


def test_timing_note_does_not_include_the_next_note_or_chapter():
    page = (
        b'<div>Unrelated</div><div><a name="12">a</a></div>'
        b"<div>Increases are effective in December after 1982.</div>"
        b'<div><a name="13">b</a>Another note</div><div>Unrelated</div>'
    )
    assert capture.cola_timing_note(page) == (
        "a Increases are effective in December after 1982."
    )


def test_capture_refuses_existing_snapshot_before_fetching(
    tmp_path, monkeypatch
):
    (tmp_path / capture.FRAGMENT_NAME).write_text("invented")

    def forbidden(*args):
        pytest.fail("existing snapshot must refuse without a fetch")

    monkeypatch.setattr(capture, "_fetch", forbidden)
    with pytest.raises(FileExistsError):
        capture.main(["--output-dir", str(tmp_path)])
