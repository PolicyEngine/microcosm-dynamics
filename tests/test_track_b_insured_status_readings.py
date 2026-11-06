"""Statutory conformance: the insured-status source-conflict register.

Invented data only; no population, behavioral or forecast claim.

Each ``# Source conflict <id>`` marker in the insured-status modules names its
reading on the marker's own line. The design note's register lists the same
readings, each with the functions that hold its markers.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "src/populace_dynamics/track_b/insured_status.py",
    "src/populace_dynamics/track_b/_insured_status_qc.py",
)
NOTE = ROOT / "docs/design/track_b_insured_status.md"
HEADING = "## Source-conflict register"
MARKER = re.compile(r"#\s*Source conflict\b(.*)$")
READING = re.compile(r"us:oasdi-insured-[a-z0-9]+(?:-[a-z0-9]+)*")
ENTRY = re.compile(
    rf"^- `({READING.pattern})`\s*\(([^)]*)\)", flags=re.MULTILINE
)


def _markers():
    """Each marker's module, line, trailing text and top-level function."""
    found = []
    for module in MODULES:
        text = (ROOT / module).read_text()
        functions = [
            node
            for node in ast.parse(text).body
            if isinstance(node, ast.FunctionDef)
        ]
        for number, line in enumerate(text.splitlines(), 1):
            match = MARKER.search(line)
            if match is None:
                continue
            enclosing = [
                node.name
                for node in functions
                if node.lineno <= number <= node.end_lineno
            ]
            found.append(
                (
                    module,
                    number,
                    match.group(1).strip(),
                    enclosing[0] if enclosing else None,
                )
            )
    return found


def _register():
    """Each register entry's reading and the functions it names."""
    text = NOTE.read_text()
    assert text.count(f"\n{HEADING}\n") == 1
    section = text.split(f"\n{HEADING}\n", 1)[1].split("\n## ", 1)[0]
    entries = ENTRY.findall(section)
    assert len(entries) == section.count("\n- "), "unparsed register entry"
    readings = [reading for reading, _ in entries]
    assert len(readings) == len(set(readings)), "duplicate register entry"
    return {
        reading: set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", sites))
        for reading, sites in entries
    }


def test_every_marker_names_its_reading_on_the_marker_line():
    markers = _markers()
    assert markers
    for module, number, rest, _ in markers:
        assert READING.fullmatch(rest), (module, number, rest)


def test_the_register_lists_exactly_the_markers_readings():
    assert {rest for _, _, rest, _ in _markers()} == set(_register())


def test_each_marker_sits_in_a_function_its_entry_names():
    register = _register()
    for module, number, rest, function in _markers():
        assert function in register.get(rest, ()), (module, number, function)


def test_each_named_function_holds_a_marker_for_its_reading():
    held = {(rest, function) for _, _, rest, function in _markers()}
    for reading, functions in _register().items():
        assert functions, reading
        for function in functions:
            assert (reading, function) in held, (reading, function)
