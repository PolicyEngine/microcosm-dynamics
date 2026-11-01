"""Invented HTML only; no public or person data supply these fixtures."""

import string
import subprocess
import sys
import unicodedata
from dataclasses import replace
from datetime import date
from decimal import Decimal
from hashlib import sha256

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.aggregate_poms import (
    _POSTAL_CODES,
    _STATES,
    _blank,
    _line_renderings,
    _own_text,
    _payment_rows,
    describe_poms_tables,
    parse_poms,
    poms_code_alternatives,
    poms_living_arrangements,
)
from populace_dynamics.income_resources.aggregate_tables import (
    PARAGRAPH_CLOSERS,
    CaptureMismatchError,
    TableSpec,
    TableStructureError,
    _HTMLTree,
    expand_html_table,
    normalized_text,
    parse_html,
)

INVENTED_HEADER = (
    "<tr><th>Federal Code</th><th>State OS Code</th><th>Category</th>"
    "<th>FBR</th><th>State Supplement Level</th>"
    "<th>Total Payment Levels</th></tr>"
)
# Runs a line of prose on past 80 characters, so it is no short line; it
# names no State, claimant word or date.
INVENTED_LONG_TAIL = (
    " (invented filler that runs this line of prose on past eighty"
    " characters)"
)
INVENTED_PREFIX = (
    "<p>Effective Dates: 02/03/2040 - Present</p>"
    "<h3>B. Description of supplements for California</h3>"
    "<table><tr><th>Code</th><th>Definition</th></tr>"
    "<tr><td>A</td><td>Invented independent arrangement</td></tr></table>"
    "<p>Monthly payment levels effective January 1, 2030</p>"
    "<h4>a. Individual payment levels for California</h4><table>"
)


def invented_spec(rows: str):
    payload = (INVENTED_PREFIX + INVENTED_HEADER + rows + "</table>").encode()
    return invented_spec_for(payload)


def invented_spec_for(payload: bytes, chart: int = 0):
    selector = describe_poms_tables(payload)[chart]
    selector["nominal_year"] = 2030
    spec = TableSpec(
        identifier="INVENTED_POMS",
        publisher="INVENTED publisher",
        edition="INVENTED edition",
        url="https://example.invalid/INVENTED",
        capture_file="INVENTED_not_read.html",
        sha256=sha256(payload).hexdigest(),
        byte_size=len(payload),
        retrieved_at="2040-02-03T00:00:00Z",
        units=("USD per month",),
        years=(2030,),
        geography=("California",),
        parser="poms",
        role="INVENTED worked example",
        selector=selector,
    )
    return spec, payload


def test_invented_flags_missing_separators_and_continued_codes():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>Aged</td>"
        "<td>1,200.00<sup>7</sup></td><td>(D)</td><td>1,300.00</td></tr>"
        "<tr><td>\u200b</td><td></td><td>Blind</td>"
        "<td>1,200.00</td><td>100.00</td><td>1,300.00</td></tr>"
    )
    cells = parse_poms(spec, payload)
    assert len(cells) == 6
    assert bool(cells[0].value == Decimal("1200"))
    assert cells[0].footnote_flags == ("7",)
    assert cells[1].value is None
    assert "suppressed" in cells[1].footnote_flags
    assert "Federal code=A" in cells[3].row_key
    assert "State OS code=A" in cells[3].row_key
    assert cells[0].effective_from == "2030-01-01"
    assert spec.selector["section_effective_from"] == "2040-02-03"
    assert poms_living_arrangements(spec, payload) == {
        "A": "Invented independent arrangement"
    }


def test_invented_stacked_source_rows_keep_separate_categories():
    spec, payload = invented_spec(
        "<tr><td>A</td><td><p>A</p><p>B</p></td>"
        "<td><p>Aged</p><p>Blind</p></td>"
        "<td><p>100</p><p>200</p></td>"
        "<td><p>10</p><p>20</p></td>"
        "<td><p>110</p><p>220</p></td></tr>"
    )
    cells = parse_poms(spec, payload)
    assert len(cells) == 6
    assert "Category=Aged" in cells[0].row_key
    assert "Category=Blind" in cells[3].row_key
    assert bool(cells[1].value == Decimal("10"))
    assert bool(cells[4].value == Decimal("20"))


def test_invented_malformed_punctuation_is_explicitly_unresolved():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>1.234.56</td><td>10</td><td>1244.56</td></tr>"
    )
    cells = parse_poms(spec, payload)
    assert cells[0].value is None
    assert "source_numeric_punctuation" in cells[0].footnote_flags


def test_invented_retroactive_dates_remain_named_options():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    payload = payload.replace(
        b"January 1, 2030", b"August 1, 2029 retroactive to January 1, 2030"
    )
    selector = describe_poms_tables(payload)[0]
    spec = replace(
        spec,
        sha256=sha256(payload).hexdigest(),
        byte_size=len(payload),
        years=(2029, 2030),
        selector=selector,
    )
    cells = parse_poms(spec, payload)
    assert spec.selector["date_options"] == {
        "source_date_1": "2029-08-01",
        "source_date_2": "2030-01-01",
    }
    assert cells[0].effective_from is None
    assert cells[0].year is None
    assert "ambiguous_effective_date" in cells[0].footnote_flags


def test_invented_direct_parser_refuses_changed_bytes():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    with pytest.raises(CaptureMismatchError, match="identity mismatch"):
        parse_poms(spec, payload + b" ")


def test_invented_blank_category_remains_explicitly_missing():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td></td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    cells = parse_poms(spec, payload)
    assert all("Category=<missing>" in cell.row_key for cell in cells)
    assert all("missing_category" in cell.footnote_flags for cell in cells)


@settings(deadline=None, max_examples=30)
@given(st.integers(min_value=0, max_value=999999), st.integers(0, 999999))
def test_invented_span_expansion_matches_shared_implementation(first, second):
    table = next(
        parse_html(
            "<table>"
            + INVENTED_HEADER
            + "<tr><td rowspan='2'>A</td><td>A</td><td>Aged</td>"
            + f"<td>{first:,}</td><td>0</td><td>{first:,}</td></tr>"
            + "<tr><td>B</td><td>Blind</td>"
            + f"<td>{second:,}</td><td>0</td><td>{second:,}</td></tr></table>"
        ).iter("table")
    )
    assert bool(_payment_rows(table) == expand_html_table(table))


@settings(deadline=None, max_examples=30)
@given(
    st.lists(st.integers(0, 999999), min_size=2, max_size=4),
    st.sampled_from(["</p>", ""]),
)
def test_invented_stacked_layout_preserves_each_amount(amounts, end):
    """Each stacked amount survives, with or without its </p>."""
    paragraphs = "".join(
        f"<p>{amount:,}<sup>x</sup>{end}" for amount in amounts
    )
    labels = "".join(
        f"<p>Category {index}{end}" for index in range(len(amounts))
    )
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td>"
        + f"<td>{labels}</td><td>{paragraphs}</td>"
        + f"<td>{paragraphs}</td><td>{paragraphs}</td></tr>"
    )
    cells = parse_poms(spec, payload)
    assert len(cells) == len(amounts) * 3
    assert bool(
        [cell.value for cell in cells[::3]] == list(map(Decimal, amounts))
    )
    assert all("x" in cell.footnote_flags for cell in cells)


def test_invented_code_footnotes_continue_with_their_codes():
    spec, payload = invented_spec(
        "<tr><td>A<sup>f</sup></td><td>A<sup>s</sup></td><td>Aged</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
        "<tr><td></td><td></td><td>Blind</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    assert all(
        cell.footnote_flags == ("f", "s") for cell in parse_poms(spec, payload)
    )


@pytest.mark.parametrize(
    ("category_paragraphs", "first_category", "second_category"),
    [
        (
            "<p>Invented group North</p><p>Invented group</p><p>South</p>",
            "Invented group North",
            "Invented group South",
        ),
        (
            "<p>Invented North</p><p></p><p>Invented South</p><p>continuation</p>",
            "Invented North",
            "Invented South continuation",
        ),
        (
            "<p>Invented North</p><p>district</p><p>Invented South</p><p>district</p>",
            "Invented North district",
            "Invented South district",
        ),
    ],
    ids=["repeated_prefix", "blank_separated", "equal_paragraph_groups"],
)
def test_invented_stacked_category_continuations(
    category_paragraphs, first_category, second_category
):
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td>"
        + f"<td>{category_paragraphs}</td>"
        + "<td><p>100</p><p>200</p></td>"
        + "<td><p>10</p><p>20</p></td>"
        + "<td><p>110</p><p>220</p></td></tr>"
    )
    cells = parse_poms(spec, payload)
    assert len(cells) == 6
    assert f"Category={first_category}" in cells[0].row_key
    assert f"Category={second_category}" in cells[3].row_key


def test_invented_merged_headers_remain_headers():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    merged = INVENTED_HEADER.replace("<th>", "<th rowspan='2'>") + "<tr></tr>"
    payload = payload.replace(INVENTED_HEADER.encode(), merged.encode())
    spec = replace(
        spec, sha256=sha256(payload).hexdigest(), byte_size=len(payload)
    )
    assert len(parse_poms(spec, payload)) == 3


def test_invented_repeated_definition_codes_are_refused():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    payload = payload.replace(
        b"<td>Invented independent arrangement</td></tr>",
        b"<td>Invented independent arrangement</td></tr>"
        b"<tr><td>A</td><td>Invented duplicate definition</td></tr>",
    )
    spec = replace(
        spec, sha256=sha256(payload).hexdigest(), byte_size=len(payload)
    )
    with pytest.raises(TableStructureError, match="blank or repeats"):
        poms_living_arrangements(spec, payload)


def test_invented_published_identity_discrepancy_is_flagged_without_repair():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>999</td></tr>"
    )
    cells = parse_poms(spec, payload)
    assert bool(cells[-1].value == Decimal("999"))
    assert all(
        "published_identity_discrepancy" in c.footnote_flags for c in cells
    )


def test_invented_header_qualifiers_survive():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    payload = payload.replace(b"FBR</th>", b"FBR<sup>header-note</sup></th>")
    spec = replace(
        spec, sha256=sha256(payload).hexdigest(), byte_size=len(payload)
    )
    cells = parse_poms(spec, payload)
    assert "header-note" in cells[0].footnote_flags
    assert "header-note" not in cells[1].footnote_flags


def test_invented_spanning_definition_code_keeps_both_descriptions():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    payload = payload.replace(
        b"<td>A</td><td>Invented independent arrangement</td></tr>",
        b"<td rowspan='2'>A</td><td>Invented independent arrangement</td></tr>"
        b"<tr><td>Invented continuation</td></tr>",
        1,
    )
    spec = replace(
        spec, sha256=sha256(payload).hexdigest(), byte_size=len(payload)
    )
    assert poms_living_arrangements(spec, payload) == {
        "A": "Invented independent arrangement Invented continuation"
    }


def test_invented_merged_numeric_header_levels_are_distinct():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    merged = (
        "<tr><th rowspan='2'>Federal Code</th>"
        "<th rowspan='2'>State OS Code</th><th rowspan='2'>Category</th>"
        "<th colspan='3'>Invented payment levels</th></tr>"
        "<tr><th>FBR</th><th>State Supplement Level</th>"
        "<th>Total Payment Levels</th></tr>"
    )
    payload = payload.replace(INVENTED_HEADER.encode(), merged.encode())
    selector = describe_poms_tables(payload)[0]
    spec = replace(
        spec,
        selector=selector,
        sha256=sha256(payload).hexdigest(),
        byte_size=len(payload),
    )
    cells = parse_poms(spec, payload)
    assert len({cell.column_key for cell in cells}) == 3
    assert cells[0].column_key == "Invented payment levels | FBR"


@pytest.mark.parametrize("long", [True, False])
def test_invented_unrelated_program_prose_does_not_replace_chart_date(long):
    """Prose that dates another program never dates the chart. A paragraph
    of 80 characters or more leaves the chart's date standing; since round
    11 a shorter one names a date no sentence states, so the chart refuses
    rather than carry an earlier date past it."""
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    prose = "A separate invented program was effective August 2029"
    prose += INVENTED_LONG_TAIL + "." if long else "."
    payload = payload.replace(
        b"<h4>a. Individual payment levels for California</h4>",
        f"<p>{prose}</p>".encode()
        + b"<h4>a. Individual payment levels for California</h4>",
    )
    if not long:
        with pytest.raises(TableStructureError, match="no effective-date"):
            describe_poms_tables(payload)
        return
    selector = describe_poms_tables(payload)[0]
    assert selector["effective_from"] == "2030-01-01"


INVENTED_CHART = (
    "<p>Monthly payment levels effective January 1, 2030</p>"
    "<h4>a. Individual payment levels for {state}</h4><table>"
    + INVENTED_HEADER
    + "<tr><td>A</td><td>A</td><td>All</td>"
    "<td>100</td><td>10</td><td>110</td></tr></table>"
)


def invented_definitions(rows) -> str:
    return (
        "<table><tr><th>Code</th><th>Definition</th></tr>"
        + "".join(
            f"<tr><td>{code}</td><td>{definition}</td></tr>"
            for code, definition in rows
        )
        + "</table>"
    )


def invented_section(state: str, groups, heading: str | None = None) -> str:
    heading = heading or f"Description of supplements for {state}"
    return (
        f"<h3>{heading}</h3>"
        + "".join(invented_definitions(group) for group in groups)
        + INVENTED_CHART.format(state=state)
    )


def invented_payload(*sections: str) -> bytes:
    return (
        "<p>Effective Dates: 02/03/2040 - Present</p>" + "".join(sections)
    ).encode()


@settings(deadline=None, max_examples=60)
@given(
    st.lists(
        st.sampled_from(string.ascii_uppercase),
        min_size=1,
        max_size=12,
        unique=True,
    ),
    st.data(),
)
def test_invented_definitions_split_across_tables_keep_the_full_mapping(
    codes, data
):
    """Splitting one State's definitions over tables loses no code."""
    mapping = {
        code: f"Invented arrangement {index}"
        for index, code in enumerate(codes)
    }
    cuts = sorted(
        data.draw(st.sets(st.integers(1, len(codes) - 1)))
        if len(codes) > 1
        else set()
    )
    bounds = [0, *cuts, len(codes)]
    groups = [
        [(code, mapping[code]) for code in codes[start:end]]
        for start, end in zip(bounds, bounds[1:], strict=False)
    ]
    payload = invented_payload(invented_section("California", groups))
    spec, payload = invented_spec_for(payload)
    assert spec.selector["definitions_table_indexes"] == list(
        range(len(groups))
    )
    assert poms_living_arrangements(spec, payload) == mapping


@pytest.mark.parametrize("agrees", [True, False])
def test_invented_cross_table_redefinition_merges_or_is_refused(agrees):
    second = "Invented arrangement" if agrees else "Invented other arrangement"
    payload = invented_payload(
        invented_section(
            "California",
            [[("A", "Invented arrangement")], [("A", second)]],
        )
    )
    spec, payload = invented_spec_for(payload)
    if agrees:
        assert poms_living_arrangements(spec, payload) == {
            "A": "Invented arrangement"
        }
    else:
        with pytest.raises(TableStructureError, match="conflicting"):
            poms_living_arrangements(spec, payload)


def test_invented_definitions_do_not_carry_into_the_next_state():
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]),
        invented_section("Nevada", [[("B", "Invented second")]]),
    )
    first, payload = invented_spec_for(payload, 0)
    second, payload = invented_spec_for(payload, 1)
    assert first.selector["state"] == "California"
    assert second.selector["state"] == "Nevada"
    assert second.selector["definitions_table_indexes"] == [2]
    assert poms_living_arrangements(second, payload) == {
        "B": "Invented second"
    }


def test_invented_postal_code_heading_names_its_state():
    """Regression: "New Jersey (NJ)" once left the prior State in place."""
    payload = invented_payload(
        invented_section("Nevada", [[("A", "Invented first")]]),
        invented_section(
            "New Jersey",
            [[("B", "Invented second")]],
            heading="K. Description of supplements - New Jersey (NJ)",
        ),
    )
    spec, payload = invented_spec_for(payload, 1)
    assert spec.selector["state"] == "New Jersey"
    assert poms_living_arrangements(spec, payload) == {"B": "Invented second"}


def test_invented_joint_definition_row_defines_each_named_code():
    payload = invented_payload(
        invented_section(
            "California",
            [[("A", "Invented first"), ("C/H", "Invented joint")]],
        )
    )
    spec, payload = invented_spec_for(payload)
    assert poms_living_arrangements(spec, payload) == {
        "A": "Invented first",
        "C": "Invented joint",
        "H": "Invented joint",
    }


def test_invented_full_width_note_row_is_not_a_code():
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]])
    ).replace(
        b"</td></tr></table>",
        b"</td></tr><tr><td colspan='2'>Invented note</td></tr></table>",
        1,
    )
    spec, payload = invented_spec_for(payload)
    assert poms_living_arrangements(spec, payload) == {"A": "Invented first"}


@settings(deadline=None, max_examples=60)
@given(
    st.lists(
        st.sampled_from(string.ascii_uppercase),
        min_size=2,
        max_size=4,
        unique=True,
    ),
    st.sampled_from(["/", " / ", " or "]),
)
def test_invented_joint_codes_name_each_single_code(codes, separator):
    assert poms_code_alternatives(separator.join(codes)) == tuple(codes)


@pytest.mark.parametrize("code", ["A", "AB", "1/2", "A or BB", "Code A"])
def test_invented_other_codes_are_returned_unchanged(code):
    assert poms_code_alternatives(code) == (code,)


def test_invented_state_named_only_in_a_date_line_is_refused():
    """A State without its own section heading has no definitions."""
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]),
        "<p>Nevada Effective 1/1/30</p>"
        + INVENTED_CHART.format(state="Nevada"),
    )
    with pytest.raises(TableStructureError, match="section heading"):
        describe_poms_tables(payload)


@pytest.mark.parametrize("close", ["", "</p>"])
def test_invented_state_heading_in_an_unclosed_paragraph_names_its_state(
    close,
):
    """Regression: an unclosed "<p>Nevada" kept California's definitions."""
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]),
        f"<p>Nevada{close}<h4>Individual</h4>"
        f"<table>{INVENTED_HEADER}</table>",
    )
    spec, payload = invented_spec_for(payload, 1)
    assert spec.selector["state"] == "Nevada"
    assert spec.selector["definitions_table_indexes"] == []
    with pytest.raises(TableStructureError, match="not identified"):
        poms_living_arrangements(spec, payload)


INVENTED_STATES = ("California", "Nevada", "Utah")


@st.composite
def invented_paragraph_sections(draw):
    """Invented State sections as ("p", text) paragraphs and other markup."""
    pieces, states = [], []
    for state in draw(
        st.lists(st.sampled_from(INVENTED_STATES), min_size=1, max_size=3)
    ):
        heading = f"Description of supplements for {state}"
        pieces.append(("p" if draw(st.booleans()) else "h3", heading))
        for code in draw(
            st.lists(st.sampled_from("ABC"), max_size=2, unique=True)
        ):
            pieces.append(
                (
                    "html",
                    invented_definitions([(code, f"Invented {state} {code}")]),
                )
            )
        for _ in range(draw(st.integers(1, 2))):
            pieces.append(
                ("p", "Monthly payment levels effective January 1, 2030")
            )
            pieces.append(("p", f"Individual payment levels for {state}"))
            pieces.append(("html", f"<table>{INVENTED_HEADER}</table>"))
            states.append(state)
    return pieces, states


def invented_piece(kind: str, body: str, close: bool, wrap: str) -> str:
    if kind == "p":
        return f"<p>{body}" + ("</p>" if close else "")
    if kind == "h3":
        # ``wrap`` puts the heading's text, or only its State, in a block.
        if wrap.startswith("state:"):
            head, state = body.rsplit(" for ", 1)
            tag = wrap.removeprefix("state:")
            body = f"{head} for <{tag}>{state}</{tag}>"
        elif wrap.startswith("follow:"):
            # A block that HTML keeps inside the heading, after its words.
            tag = wrap.removeprefix("follow:")
            return f"<h3>{body}<{tag}>Invented note</{tag}></h3>"
        elif wrap == "end:h4":
            # Any heading end tag ends the open heading.
            return f"<h3>{body}</h4>"
        elif wrap:
            body = f"<{wrap}>{body}</{wrap}>"
        return f"<h3>{body}</h3>"
    return body


def invented_rendering(pieces, closed, wraps=None) -> bytes:
    wraps = wraps or [""] * len(pieces)
    return invented_payload(
        *(
            invented_piece(kind, body, close, wrap)
            for (kind, body), close, wrap in zip(
                pieces, closed, wraps, strict=True
            )
        )
    )


def poms_outcome(payload: bytes):
    try:
        return describe_poms_tables(payload)
    except TableStructureError as error:
        return str(error)


@settings(deadline=None, max_examples=100)
@given(invented_paragraph_sections(), st.data())
def test_invented_selectors_do_not_depend_on_omitted_paragraph_ends(
    sections, data
):
    """HTML lets a paragraph end without </p>; the selectors are the same."""
    pieces, states = sections
    closed = data.draw(
        st.lists(st.booleans(), min_size=len(pieces), max_size=len(pieces))
    )
    explicit = poms_outcome(invented_rendering(pieces, [True] * len(pieces)))
    assert poms_outcome(invented_rendering(pieces, closed)) == explicit
    if not isinstance(explicit, str):
        assert [context["state"] for context in explicit] == states


@settings(deadline=None, max_examples=100)
@given(
    st.recursive(
        st.text("Invented ab\n\t", max_size=6),
        lambda inner: st.tuples(
            st.sampled_from(["span", "b", "a", "em", "sup"]),
            st.lists(inner, max_size=3),
        ).map(
            lambda node: f"<{node[0]}>" + "".join(node[1]) + f"</{node[0]}>"
        ),
        max_leaves=8,
    ),
    st.sampled_from(["p", "h3"]),
)
def test_invented_block_without_nested_blocks_reads_its_full_text(inline, tag):
    """Inline elements join without a separator, as HTML renders them, and
    whitespace collapses."""
    block = next(parse_html(f"<{tag}>{inline}</{tag}>").iter(tag))
    assert _own_text(block) == " ".join("".join(block.itertext()).split())


def invented_nevada_after_california(nevada_heading: str) -> bytes:
    return invented_payload(
        invented_section("California", [[("A", "Invented first")]]),
        nevada_heading
        + f"<h4>Individual</h4><table>{INVENTED_HEADER}</table>",
    )


@pytest.mark.parametrize(
    "heading",
    [
        "<h3><div>Nevada</div></h3>",
        "<h3><div>Description of supplements for Nevada</div></h3>",
        "<h3>Description of supplements for <div>Nevada</div></h3>",
        "<h3><span><div>Nevada</div></span></h3>",
        "<h3><section>Nevada</section></h3>",
        "<h3><p>Nevada</p></h3>",
        "<div>Description of supplements for Nevada</div>",
        "<p><div>Nevada</div></p>",
    ],
)
def test_invented_state_heading_inside_or_as_a_block_names_its_state(
    heading,
):
    """Regression: a block inside a heading cut its text, keeping California."""
    spec, payload = invented_spec_for(
        invented_nevada_after_california(heading), 1
    )
    assert spec.selector["state"] == "Nevada"
    assert spec.selector["definitions_table_indexes"] == []
    with pytest.raises(TableStructureError, match="not identified"):
        poms_living_arrangements(spec, payload)


# The start tags whose WHATWG "in body" rules close an open paragraph, copied
# from the specification rather than from the reader.
SPEC_PARAGRAPH_CLOSERS = (
    "address article aside blockquote center details dialog dir div dl "
    "fieldset figcaption figure footer header hgroup main menu nav ol p "
    "search section summary ul h1 h2 h3 h4 h5 h6 pre listing form li dd "
    "dt plaintext table hr xmp"
).split()


def test_invented_every_paragraph_closer_ends_a_state_heading():
    """Each start tag that ends an open paragraph in HTML ends it here. A
    plaintext start tag ends it too, but its page refuses
    (``test_invented_plaintext_start_tag_refuses_the_page``)."""
    assert set(SPEC_PARAGRAPH_CLOSERS) == PARAGRAPH_CLOSERS
    for closer in SPEC_PARAGRAPH_CLOSERS:
        # Text inside the closer would join the heading if it did not end it.
        block = (
            "<hr>Invented note"
            if closer == "hr"
            else f"<{closer}>Invented note</{closer}>"
        )
        for close in ("", "</p>"):
            page = invented_nevada_after_california(f"<p>Nevada{close}{block}")
            if closer == "plaintext":
                with pytest.raises(TableStructureError, match="plaintext"):
                    describe_poms_tables(page)
                continue
            spec, _ = invented_spec_for(page, 1)
            assert spec.selector["state"] == "Nevada", closer
            assert spec.selector["definitions_table_indexes"] == [], closer


@pytest.mark.parametrize(
    "page",
    [
        "<p>Nevada<plaintext>Invented note</plaintext>",
        "<p>Nevada<PLAINTEXT>Invented note",
        "<p>Nevada<plaintext/>Invented note",
    ],
)
def test_invented_plaintext_start_tag_refuses_the_page(page):
    """HTML reads the rest of a page after a plaintext start tag as text, as
    Python 3.14 does and 3.13 does not, so the page refuses on both."""
    with pytest.raises(TableStructureError, match="plaintext"):
        parse_html(page)


# HTML's raw text elements, whose content is text up to the matching end
# tag, copied from the WHATWG rules rather than from the tree. noscript is
# one only with scripting on; the tree reads HTML with scripting off.
SPEC_RAW_TEXT = ("script", "style", "xmp", "iframe", "noembed", "noframes")


@pytest.mark.parametrize("tag", [*SPEC_RAW_TEXT, "XMP"])
def test_invented_raw_text_element_holds_its_markup_as_text(tag):
    """Python 3.13 reads only script and style as raw text and 3.14 all six;
    the tree reads all six on both. Expected values are html5lib 1.1's."""
    assert set(_HTMLTree.CDATA_CONTENT_ELEMENTS) == set(SPEC_RAW_TEXT)
    root = parse_html(
        f"<div>w0<{tag}><b>w1</b><p>w2&amp;w3</{tag}>w4<b>w5</b></div>"
    )
    (element,) = root.iter(tag.lower())
    assert element.text == "<b>w1</b><p>w2&amp;w3"
    assert len(element) == 0
    # Markup after the end tag is read as markup again.
    assert [b.text for b in root.iter("b")] == ["w5"]


def test_invented_noscript_content_is_markup():
    """With scripting off, as in html5lib 1.1 and both Python versions,
    noscript holds elements, not text."""
    page = "<p>w0<noscript><b>w1</b><p>w2</noscript>w3"
    assert invented_blocks(page) == [("p", "w0 w1"), ("p", "w2w3")]
    assert [c.tag for c in parse_html(page).find(".//noscript")] == ["b"]


@pytest.mark.parametrize("tag", ["xmp", "iframe", "script"])
def test_invented_raw_text_left_open_keeps_its_text(tag):
    """The end of the page ends a raw text element left open, and its text
    is kept, as html5lib 1.1 keeps it."""
    root = parse_html(f"<p>w0<{tag}>w1<b>w2")
    assert root.find(f".//{tag}").text == "w1<b>w2"


@pytest.mark.parametrize("comment", ["<!-->", "<!--->"])
def test_invented_abruptly_closed_comment_refuses_the_page(comment):
    """HTML ends "<!-->" and "<!--->" as empty comments. Python 3.14 does
    too, while 3.13 runs either on to a later "-->", hiding the text
    between, so the page refuses on both."""
    with pytest.raises(TableStructureError, match="comment"):
        parse_html(f"<h3>Nevada</h3><p>w0{comment}w1-->w2</p>")


@pytest.mark.parametrize(
    "comment", ["<!---->", "<!-- w9 -->", "<!-- <!-- -->", "<!--x->-->"]
)
def test_invented_other_comments_hide_only_themselves(comment):
    """Every other comment ends at its first "-->", on both versions, and
    the text around it joins as HTML renders it."""
    root = parse_html(f"<p>w0{comment}w1</p>")
    assert normalized_text(root.find(".//p")) == "w0w1"


def test_invented_effective_date_inside_a_heading_block_is_read():
    payload = invented_payload(
        "<h3>Description of supplements for California</h3>"
        + invented_definitions([("A", "Invented first")])
        + "<h5>Monthly payment levels effective "
        "<div>January 1, 2031</div></h5>"
        + f"<h4>Individual</h4><table>{INVENTED_HEADER}</table>"
    )
    spec, _ = invented_spec_for(payload)
    assert spec.selector["effective_from"] == "2031-01-01"


def test_invented_state_date_line_inside_a_heading_is_still_refused():
    payload = invented_nevada_after_california(
        "<h3>Nevada<div>Effective 1/1/30</div></h3>"
    )
    with pytest.raises(TableStructureError, match="section heading"):
        describe_poms_tables(payload)


@pytest.mark.parametrize("close", ["", "</h3>"])
def test_invented_heading_left_open_before_its_table_names_its_state(close):
    """Regression: an open heading once read its tables as heading text."""
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]),
        f"<h3>Description of supplements for Nevada{close}"
        + invented_definitions([("B", "Invented second")])
        + INVENTED_CHART.format(state="Nevada"),
    )
    spec, payload = invented_spec_for(payload, 1)
    assert spec.selector["state"] == "Nevada"
    assert poms_living_arrangements(spec, payload) == {"B": "Invented second"}


@settings(deadline=None, max_examples=100)
@given(invented_paragraph_sections(), st.data())
def test_invented_selectors_do_not_depend_on_blocks_inside_headings(
    sections, data
):
    """HTML keeps blocks inside a heading; its text, and selectors, stay."""
    pieces, _ = sections
    wraps = [
        (
            data.draw(
                st.sampled_from(
                    ["", "div", "section", "p", "blockquote"]
                    + ["state:div", "state:section", "state:span"]
                    + ["follow:div", "follow:p", "follow:section"]
                    + ["end:h4"]
                )
            )
            if kind == "h3"
            else ""
        )
        for kind, _ in pieces
    ]
    closed = [True] * len(pieces)
    assert poms_outcome(
        invented_rendering(pieces, closed, wraps)
    ) == poms_outcome(invented_rendering(pieces, closed))


@pytest.mark.parametrize(
    ("before", "message"),
    [
        # Before any State heading, the chart itself refuses.
        ("", "lacks state or claimant context"),
        ("California", "names another State"),
    ],
)
def test_invented_claimant_line_naming_another_state_is_refused(
    before, message
):
    """A State whose heading went unread refuses at its claimant line."""
    section = (
        invented_section("California", [[("A", "Invented first")]])
        if before
        else ""
    )
    payload = invented_payload(
        section,
        "<p>Invented heading the reader does not know</p>"
        + INVENTED_CHART.format(state="Nevada"),
    )
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    ("filler", "after"),
    [("<p>Invented filler" * 2400, ""), ("<div>" * 3000, "</div>" * 3000)],
    ids=["unclosed_paragraphs", "nested_divs"],
)
def test_invented_deep_pages_read_without_recursion(filler, after):
    """Regression: thousands of unclosed paragraphs exhausted the stack."""
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]),
        filler,
        invented_section("Nevada", [[("B", "Invented second")]]),
        after,
    )
    states = [c["state"] for c in describe_poms_tables(payload)]
    assert states == ["California", "Nevada"]


@settings(deadline=None, max_examples=100)
@given(
    st.lists(
        st.lists(
            st.tuples(
                st.text("Invented 0123456789 ", min_size=1, max_size=8),
                st.booleans(),
                st.booleans(),
            ),
            min_size=1,
            max_size=4,
        ),
        min_size=1,
        max_size=4,
    )
)
def test_invented_optional_cell_and_paragraph_ends_keep_the_grid(rows):
    """HTML lets td, tr and p end without end tags; the grid is the same."""

    def render(explicit: bool) -> str:
        return (
            "<table>"
            + "".join(
                "<tr>"
                + "".join(
                    "<td>"
                    + (f"<p>{text}" if in_paragraph else text)
                    + ("</p>" if in_paragraph and explicit else "")
                    + ("</td>" if explicit or end else "")
                    for text, in_paragraph, end in row
                )
                + ("</tr>" if explicit else "")
                for row in rows
            )
            + "</table>"
        )

    def grid(html: str):
        table = parse_html(html).find("table")
        return [
            [_blank(c.text) for c in row] for row in expand_html_table(table)
        ]

    assert grid(render(False)) == grid(render(True))


@pytest.mark.parametrize(
    "heading",
    [
        "<h3>Nevada<p>Invented note</p>",
        "<h3>Nevada<p>Monthly payment levels effective January 1, 2030</p>",
        "<h3>Nevada<div>Invented subtitle</div></h3>",
        "<h3>Nevada<p>Invented subtitle</p></h3>",
        "<h3>Nevada</h4><p>Invented note</p>",
        "<h3>Description of supplements for Nevada<section>Invented"
        "</section></h3>",
        # The State follows the nested block, in the heading's own text.
        "<h3><div>Invented subtitle</div>Nevada</h3>",
        "<h3><p>Invented subtitle</p>Description of supplements for Nevada",
        # A div's own text ends at a block nested in it.
        "<div>Description of supplements for Nevada<div>Invented</div></div>",
    ],
)
def test_invented_block_after_a_state_heading_does_not_hide_it(heading):
    """Regression: a block after a heading's words kept California."""
    spec, payload = invented_spec_for(
        invented_nevada_after_california(heading), 1
    )
    assert spec.selector["state"] == "Nevada"
    assert spec.selector["definitions_table_indexes"] == []


@pytest.mark.parametrize(
    "line",
    [
        "<h4>Individual<p>Invented note</p>",
        "<h4>Individual<div>Invented note</div></h4>",
        "<h4>Individual</h5>",
    ],
)
def test_invented_block_after_a_claimant_heading_does_not_hide_it(line):
    """Regression: a block after "Individual" kept the couple claimant."""
    chart = f"<table>{INVENTED_HEADER}</table>"
    payload = invented_payload(
        "<h3>Description of supplements for California</h3>"
        + invented_definitions([("A", "Invented first")])
        + "<h4>Couple</h4>"
        + chart
        + line
        + chart
    )
    assert [c["claimant_type"] for c in describe_poms_tables(payload)] == [
        "couple",
        "individual",
    ]


def test_invented_effective_line_after_heading_words_is_read():
    payload = invented_payload(
        "<h3>Description of supplements for California</h3>"
        + invented_definitions([("A", "Invented first")])
        # The date line is the heading's own text after a nested block.
        + "<h5><div>Invented note</div>Effective January 1, 2031</h5>"
        + f"<h4>Individual</h4><table>{INVENTED_HEADER}</table>"
    )
    spec, _ = invented_spec_for(payload)
    assert spec.selector["effective_from"] == "2031-01-01"


def test_invented_table_inside_an_open_heading_is_not_heading_text():
    """HTML nests a table in a heading left open; it is read as a table."""
    spec, _ = invented_spec_for(
        invented_nevada_after_california(
            "<h3>Description of supplements for Nevada"
            "<table><tr><td>Utah</td></tr></table>"
        ),
        1,
    )
    assert spec.selector["state"] == "Nevada"


def test_invented_heading_whose_lines_name_two_states_is_refused():
    payload = invented_nevada_after_california(
        "<h3>Nevada<div>Utah</div></h3>"
    )
    with pytest.raises(TableStructureError, match="names two States"):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    "page",
    [
        "<h3>"
        + "<div>" * 1500
        + "Description of supplements for Nevada"
        + "</div>" * 1500
        + "</h3>",
        "<p>" + "<span>" * 1500 + "Nevada" + "</span>" * 1500 + "</p>",
        "<h3>" + "<span>" * 1500 + "Nevada",
    ],
    ids=["divs_in_heading", "spans_in_paragraph", "open_spans_in_heading"],
)
def test_invented_deeply_nested_heading_text_reads_without_recursion(page):
    """Regression: a heading's own text was collected recursively."""
    spec, _ = invented_spec_for(invented_nevada_after_california(page), 1)
    assert spec.selector["state"] == "Nevada"


def test_invented_claimant_line_before_any_state_heading_is_not_refused():
    """With no State yet, a chart would refuse, and a heading resets it."""
    payload = invented_payload(
        "<p>Individual payment levels for Nevada</p>",
        invented_section("California", [[("A", "Invented first")]]),
    )
    assert [c["state"] for c in describe_poms_tables(payload)] == [
        "California"
    ]


@pytest.mark.parametrize(
    ("line", "claimant"),
    [
        ("Individual payment levels for Washington, D.C.", "individual"),
        ("Couple for Washington, D.C.", "couple"),
        # Round 9 pinned this line as individual, its first word, and round
        # 10 as prose that names no claimant, so the chart refused "lacks
        # state or claimant context". A heading that holds two claimant
        # types refuses as naming two, claimant line or not.
        ("Individual or couple for Washington, D.C.", None),
    ],
)
def test_invented_washington_dc_names_the_district(line, claimant):
    payload = invented_payload(
        invented_section(
            "District of Columbia", [[("A", "Invented first")]]
        ).replace(
            "a. Individual payment levels for District of Columbia", line
        )
    )
    if claimant is None:
        with pytest.raises(TableStructureError, match="two claimants"):
            describe_poms_tables(payload)
        return
    (context,) = describe_poms_tables(payload)
    assert context["state"] == "District of Columbia"
    assert context["claimant_type"] == claimant


def invented_grid(html: str) -> list[list[str]]:
    table = parse_html(html).find(".//table")
    return [[_blank(c.text) for c in row] for row in expand_html_table(table)]


@pytest.mark.parametrize("section", ["thead", "tbody", "tfoot"])
def test_invented_table_section_start_ends_the_open_cell(section):
    """Regression: a section start tag left the open header cell open."""
    html = (
        "<table><thead><tr><th>Row<th>Col A<th>Col B"
        f"<{section}><tr><td>Label<td>1<td>2</table>"
    )
    assert invented_grid(html) == [
        ["Row", "Col A", "Col B"],
        ["Label", "1", "2"],
    ]


@pytest.mark.parametrize("tag", ["caption", "colgroup"])
def test_invented_caption_or_colgroup_start_ends_the_open_row(tag):
    html = f"<table><tr><td>a<td>b<{tag}><tr><td>c<td>d</table>"
    assert invented_grid(html) == [["a", "b"], ["c", "d"]]


@pytest.mark.parametrize("start", ["<tr>", "<td>", "<th>"])
def test_invented_row_or_cell_start_ends_an_open_caption(start):
    table = parse_html(
        f"<table><caption>Invented caption{start}a</table>"
    ).find(".//table")
    caption = table.find("caption")
    assert normalized_text(caption) == "Invented caption"
    assert caption.find(".//tr") is None
    assert caption.find(".//td") is None and caption.find(".//th") is None


def test_invented_row_start_ends_the_open_row():
    """HTML never nests a row in a row."""
    table = parse_html("<table><tr><td>a<tr><td>b</table>").find(".//table")
    rows = list(table.iter("tr"))
    assert len(rows) == 2
    assert all(row.find(".//tr") is None for row in rows)


@pytest.mark.parametrize("end", ["</h3>", "</h4>", "</h1>"])
def test_invented_any_heading_end_tag_ends_the_open_heading(end):
    root = parse_html(f"<h3>Invented heading{end}<p>Invented note</p>")
    assert root.find(".//h3//p") is None
    assert normalized_text(root.find(".//h3")) == "Invented heading"


def test_invented_heading_end_tag_stops_at_its_scope():
    """A heading end tag inside a cell does not end a heading outside it."""
    root = parse_html(
        "<h3>Invented<table><tr><td>a</h4>b</td></tr></table>c</h3>"
    )
    # The ignored end tag leaves "a" and "b" as one run of cell text.
    assert normalized_text(root.find(".//td")) == "ab"
    assert root.find(".//h3//table") is not None


def test_invented_heading_start_ends_only_a_heading_that_is_current():
    """HTML pops an open heading only when it is the current node."""
    root = parse_html("<h3><span>Invented<h4>Other</h4></span></h3>")
    assert root.find(".//h3//h4") is not None
    root = parse_html("<h3>Invented<h4>Other</h4>")
    assert root.find(".//h3//h4") is None


def test_invented_definition_table_after_a_chart_is_refused():
    """Regression: a later table once defined codes for later charts only."""
    payload = invented_payload(
        "<h3>Description of supplements for California</h3>"
        + invented_definitions([("A", "Invented first")])
        + INVENTED_CHART.format(state="California")
        + invented_definitions([("B", "Invented second")])
        + INVENTED_CHART.format(state="California")
    )
    with pytest.raises(TableStructureError, match="follows a payment chart"):
        describe_poms_tables(payload)


@settings(deadline=None, max_examples=60)
@given(
    st.lists(
        st.sampled_from(["definitions", "chart"]), min_size=1, max_size=8
    ).filter(lambda kinds: "chart" in kinds),
    st.data(),
)
def test_invented_interleaved_definitions_are_read_in_full_or_refused(
    kinds, data
):
    """Each chart reads every table of its section, or the section refuses.

    The tables of one State section arrive in any order. A definition table
    after a chart refuses; otherwise every chart reads every definition
    table of its section, and a section with none refuses at the reader.
    """
    codes = iter(string.ascii_uppercase)
    groups = {
        index: [
            (next(codes), f"Invented arrangement {index}.{row}")
            for row in range(data.draw(st.integers(1, 2)))
        ]
        for index, kind in enumerate(kinds)
        if kind == "definitions"
    }
    payload = invented_payload(
        "<h3>Description of supplements for California</h3>"
        + "".join(
            (
                invented_definitions(groups[index])
                if kind == "definitions"
                else INVENTED_CHART.format(state="California")
            )
            for index, kind in enumerate(kinds)
        )
    )
    if "definitions" in kinds[kinds.index("chart") :]:
        with pytest.raises(TableStructureError, match="follows a payment"):
            describe_poms_tables(payload)
        return
    mapping = {code: text for group in groups.values() for code, text in group}
    for chart in range(kinds.count("chart")):
        spec, payload = invented_spec_for(payload, chart)
        assert spec.selector["definitions_table_indexes"] == sorted(groups)
        if not groups:
            with pytest.raises(TableStructureError, match="not identified"):
                poms_living_arrangements(spec, payload)
            continue
        assert poms_living_arrangements(spec, payload) == mapping


INVENTED_TAGS = ("p", "div", "h3", "h4", "span", "b", "table", "td", "ul")


@settings(deadline=None, max_examples=200)
@given(
    st.lists(
        st.tuples(st.sampled_from(INVENTED_TAGS), st.sampled_from(["", "/"])),
        max_size=30,
    )
)
def test_invented_tree_ends_paragraphs_and_headings_as_html_does(tokens):
    """No paragraph holds a block that HTML says ends it, end tag or not.

    A paragraph closer nests under a paragraph only across a cell, table or
    other button-scope boundary, and a heading never holds a heading as its
    direct child.
    """
    document = parse_html(
        "".join(f"<{end}{tag}>Invented" for tag, end in tokens)
    )
    boundaries = {"td", "th", "table", "caption", "button"}

    def check(node, open_paragraph: bool) -> None:
        for child in node:
            assert not (open_paragraph and child.tag in PARAGRAPH_CLOSERS)
            if node.tag in {"h3", "h4"}:
                assert child.tag not in {"h3", "h4"}
            check(
                child,
                (open_paragraph or child.tag == "p")
                and child.tag not in boundaries,
            )

    check(document, False)


@pytest.mark.parametrize("close", ["", "</h3>"])
@pytest.mark.parametrize("block", ["section", "blockquote", "li"])
@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("Utah Effective January 1, 2031", "section heading"),
        ("Couple for Utah", "names another State"),
    ],
    ids=["date_line", "claimant_line"],
)
def test_invented_line_nested_in_a_heading_passes_the_state_guards(
    close, block, line, message
):
    """Regression: a date or claimant line HTML kept inside a heading left
    open skipped both State guards; it now refuses, as after a closed one."""
    nested = (
        f"<ul><li>{line}</ul>"
        if block == "li"
        else f"<{block}>{line}</{block}>"
    )
    payload = invented_nevada_after_california(f"<h3>Nevada{close}{nested}")
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(payload)


def test_invented_claimant_guard_reads_every_claimant_line():
    """Regression: only a heading's first claimant line was guarded, and its
    whole text, which also names its section's State, covered the rest."""
    payload = invented_nevada_after_california(
        "<h3>Nevada</h3><h4>Individual for Nevada<br>Couple for Utah</h4>"
    )
    with pytest.raises(TableStructureError, match="names another State"):
        describe_poms_tables(payload)


INVENTED_BLOCK_KINDS = ("p", "div", "section", "blockquote", "li", "article")


def invented_block(kind: str, body: str, block: str, open_: bool) -> str:
    """Render a piece with its line in ``block``, or a heading left open."""
    if kind == "h3":
        return f"<h3>{body}" + ("" if open_ else "</h3>")
    if kind == "p":
        if block == "li":
            return f"<ul><li>{body}</ul>"
        return f"<{block}>{body}</{block}>"
    return body


@settings(deadline=None, max_examples=100)
@given(invented_paragraph_sections(), st.data())
def test_invented_selectors_do_not_depend_on_heading_ends_or_block_kinds(
    sections, data
):
    """A heading left open holds the blocks HTML nests in it, and a State
    heading, date or claimant line may sit in any of these blocks; the
    selectors are those of closed headings and paragraphs."""
    pieces, states = sections
    blocks = [data.draw(st.sampled_from(INVENTED_BLOCK_KINDS)) for _ in pieces]
    left_open = [data.draw(st.booleans()) for _ in pieces]
    explicit = poms_outcome(invented_rendering(pieces, [True] * len(pieces)))
    varied = invented_payload(
        *(
            invented_block(kind, body, block, open_)
            for (kind, body), block, open_ in zip(
                pieces, blocks, left_open, strict=True
            )
        )
    )
    assert poms_outcome(varied) == explicit
    if not isinstance(explicit, str):
        assert [context["state"] for context in explicit] == states


@pytest.mark.parametrize(
    "heading",
    [
        "<h3>Nevada<br>Invented note</h3>",
        "<h3>Invented note<br>Nevada</h3>",
        "<h3>Nevada<br></br>Invented note</h3>",
        "<h3>Nevada</p>Invented note</h3>",
        "<h3>Nevada&#8203;</h3>",
        "<h3>Invented note<br>Nevada&#8204;</h3>",
        "<h3>Nev&shy;ada</h3>",
        "<h3>&#65279;Description of supplements for Nevada</h3>",
        "<div>Nevada<br>Invented note</div>",
        "<p>Description of supplements for Nevada<br>Invented note</p>",
        "<ul><li>Description of supplements for Nevada</ul>",
    ],
)
def test_invented_line_break_or_zero_width_character_keeps_a_state_heading(
    heading,
):
    """Regression: a br or zero-width character kept California's selector."""
    spec, _ = invented_spec_for(invented_nevada_after_california(heading), 1)
    assert spec.selector["state"] == "Nevada"
    assert spec.selector["definitions_table_indexes"] == []


@pytest.mark.parametrize(
    "heading",
    [
        "<h3>Nevada <small>(Invented)</small></h3>",
        "<h3>New York (NJ)</h3>",
        "<h3>Washington (DC)</h3>",
        "<h3>Invented note on Nevada</h3>",
        "<h3>Invented note on Nevada<br>Invented note</h3>",
    ],
)
def test_invented_heading_naming_a_state_it_does_not_head_is_refused(
    heading,
):
    """Regression: these headings kept California's definitions silently."""
    with pytest.raises(TableStructureError, match="does not head"):
        describe_poms_tables(invented_nevada_after_california(heading))


def test_invented_heading_naming_its_own_state_is_admitted():
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]).replace(
            "<p>Monthly", "<h4>Invented note on California</h4><p>Monthly"
        )
    )
    (context,) = describe_poms_tables(payload)
    assert context["state"] == "California"


@pytest.mark.parametrize(
    "block",
    [
        "<h4>Invented note<br>Invented note on Nevada</h4>",
        "<h4>Invented note<br>Nevada <small>(Invented)</small></h4>",
        "<h4>Invented note<br>Nevada (continued)</h4>",
        "<h4>Invented note<br>State of Nevada</h4>",
        "<h5>Invented note<br>Invented<br>Notes on Nevada</h5>",
        "<h4>Invented note<br>Invented note (NV)</h4>",
    ],
)
def test_invented_later_heading_line_naming_another_state_is_refused(block):
    """Round 8 admitted a heading whose later line named another State,
    since only a heading's first line was netted. A heading is short, and
    a State it names but does not head is one this reader cannot tell
    from a section break, so every line of h1-h6 is netted now."""
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]).replace(
            "<p>Monthly", block + "<p>Monthly"
        )
    )
    with pytest.raises(TableStructureError, match="does not head"):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    "block",
    [
        # A later heading line may name the section's own State.
        "<h4>Invented note<br>Invented note on California</h4>",
        "<h4>Invented note<br>Invented note (CA)</h4>",
        # A long paragraph that names another State is prose, not a
        # heading; a short one refuses (the short-line State net).
        f"<p>Invented note on Nevada{INVENTED_LONG_TAIL}</p>",
    ],
)
def test_invented_later_heading_line_own_state_or_paragraph_is_admitted(
    block,
):
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]).replace(
            "<p>Monthly", block + "<p>Monthly"
        )
    )
    (context,) = describe_poms_tables(payload)
    assert context["state"] == "California"


def test_invented_line_after_a_br_dating_another_state_is_refused():
    """A br-separated line that dates another State refuses, as a block
    whose whole text does."""
    payload = invented_payload(
        invented_section("California", [[("A", "Invented first")]]).replace(
            "<p>Monthly",
            "<p>Invented note<br>Nevada Effective 1/1/30</p><p>Monthly",
        )
    )
    with pytest.raises(TableStructureError, match="section heading"):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    "heading",
    [
        "Washington, D.C.",
        "Description of supplements for Washington, D.C.",
        "Washington DC",
        "Washington, DC (DC)",
    ],
)
def test_invented_washington_dc_heading_names_the_district(heading):
    """Regression: a "Washington, D.C." heading kept the prior State."""
    spec, _ = invented_spec_for(
        invented_nevada_after_california(f"<h3>{heading}</h3>"), 1
    )
    assert spec.selector["state"] == "District of Columbia"
    assert spec.selector["definitions_table_indexes"] == []


def invented_nevada_with(fragment: str, before: str = "") -> bytes:
    """A Nevada section whose chart follows ``fragment``, after its own
    definitions, date and claimant heading, with ``before`` ahead of it."""
    return invented_payload(
        before
        + "<h3>Nevada</h3>"
        + invented_definitions([("A", "Invented Nevada definition")])
        + "<p>Monthly payment levels effective January 1, 2030</p>"
        "<h4>Individual</h4>" + fragment + f"<table>{INVENTED_HEADER}</table>"
    )


def invented_selector(payload: bytes):
    (context,) = describe_poms_tables(payload)
    return (
        context["state"],
        context["claimant_type"],
        context["effective_from"],
        context["definitions_table_indexes"],
    )


def test_invented_nevada_control_reads_its_own_section():
    assert invented_selector(invented_nevada_with("")) == (
        "Nevada",
        "individual",
        "2030-01-01",
        [0],
    )


# Long enough that the whole text is no effective-date or claimant line.
INVENTED_FILLER = "<br>" + "Invented filler " * 30 + "<br>"


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        (
            "<h4>Nevada Effective January 1, 2031<br>"
            "Utah Effective January 1, 2032</h4>",
            "section heading",
        ),
        (
            "<h4>Nevada Effective January 1, 2031<br>Couple for Utah</h4>",
            "section heading",
        ),
        (
            "<h4>Nevada Effective January 1, 2031"
            + INVENTED_FILLER
            + "Utah Effective January 1, 2032</h4>",
            "section heading",
        ),
        (
            "<h4>Nevada Effective January 1, 2031"
            + INVENTED_FILLER
            + "Couple for Utah</h4>",
            "names another State",
        ),
        (
            "<h4>Nevada Effective January 1, 2031<br>Utah</h4>",
            "section heading",
        ),
        # The round-8 review's E1, E2 and E3.
        (
            "<h4>Nevada Effective January 1, 2031"
            + INVENTED_FILLER
            + "Utah</h4>",
            "section heading",
        ),
        (
            "<h4>Nevada Effective January 1, 2031"
            + INVENTED_FILLER
            + "Description of supplements for Utah</h4>",
            "section heading",
        ),
        (
            "<p>Nevada Effective January 1, 2031"
            + INVENTED_FILLER
            + "Utah (UT)</p>",
            "section heading",
        ),
    ],
    ids=[
        "date_line",
        "claimant_line",
        "long_date_line",
        "long_claimant_line",
        "heading_line",
        "long_heading_line",
        "long_heading_line_supplements",
        "long_heading_line_code",
    ],
)
def test_invented_lines_after_a_whole_text_state_date_are_guarded(
    fragment, message
):
    """Regression: a block whose whole text is a State date line skipped
    its lines, so a later line could date, head or name another State. A
    short whole text refused only as an effective-date sentence naming
    another State, and a long one, which is no such sentence, read the
    section on. Each line now passes the State guards, and a line shaped
    as another State's heading refuses, whatever the whole text's length:
    a date line's lines do not head a section, so that State's section
    was not read."""
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_whole_text_state_date_lines_do_not_head_a_section():
    """A whole-text date line's own lines still date the section and name
    its claimant, but do not head it."""
    payload = invented_nevada_with(
        "<h4>Nevada Effective January 1, 2031<br>Couple</h4>"
    )
    assert invented_selector(payload) == (
        "Nevada",
        "couple",
        "2031-01-01",
        [0],
    )


@pytest.mark.parametrize(
    ("line", "refused"),
    [
        ("Couple for Utah (see Nevada)", True),
        ("Couple for Nevada and Utah", True),
        ("Couple for Nevada", False),
        # A claimant line with no space before its claimant word.
        ("1)Couple for Utah", True),
    ],
)
def test_invented_claimant_line_may_name_only_its_own_state(line, refused):
    """Regression: a claimant line that named another State beside its own
    passed the guard."""
    payload = invented_nevada_with(f"<p>{line}</p>")
    if refused:
        with pytest.raises(TableStructureError, match="names another State"):
            describe_poms_tables(payload)
    else:
        assert invented_selector(payload)[:2] == ("Nevada", "couple")


@pytest.mark.parametrize(
    ("later", "refused"),
    [("Couple for Utah", True), ("Individual for Nevada", False)],
)
def test_invented_claimant_lines_after_the_first_are_guarded(later, refused):
    """Every claimant line of a block is guarded, not only the first. With
    the whole text too long to read as a claimant line, a later line naming
    another State still refuses; lines naming one claimant name it."""
    payload = invented_nevada_with(
        f"<p>Individual<br>{later}{INVENTED_FILLER}</p>"
    )
    if refused:
        with pytest.raises(TableStructureError, match="names another State"):
            describe_poms_tables(payload)
    else:
        assert invented_selector(payload)[:2] == ("Nevada", "individual")


@pytest.mark.parametrize(
    "fragment",
    [
        # The round-8 review's four forms, each read silently before.
        "<h4>Individual<br>Couple</h4>",
        "<h4>Individual for Nevada<br>Couple for Nevada</h4>",
        "<h4>Couple<br>Individual</h4>",
        "<h4>Couple for Nevada<br>Individual for Nevada</h4>",
        # The whole text too long to be a claimant line.
        f"<p>Individual<br>Couple{INVENTED_FILLER}</p>",
        # A block HTML keeps inside a heading left open.
        "<h4>Couple<div>Individual</div></h4>",
        # Two lines name one claimant, a third the other.
        "<p>Couple for Nevada<br>Individual<br>Couple</p>",
    ],
)
def test_invented_block_naming_two_claimants_is_refused(fragment):
    """Regression: a block whose lines named two claimant types charted
    whichever line was read last or first, without refusing."""
    with pytest.raises(TableStructureError, match="two claimants"):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    ("fragment", "claimant"),
    [
        ("<p>Couple<br>Couple payment levels</p>", "couple"),
        ("<p>Individual<br>Recipient for Nevada</p>", "individual"),
    ],
)
def test_invented_block_naming_one_claimant_names_it(fragment, claimant):
    """Lines that name one claimant type, in any of its words, name it."""
    assert invented_selector(invented_nevada_with(fragment))[:2] == (
        "Nevada",
        claimant,
    )


@pytest.mark.parametrize("line", ["<h4>Couples</h4>", "<p>Invented note</p>"])
def test_invented_second_chart_needs_its_own_claimant_line(line):
    """Regression: a second chart after a block that names no claimant took
    the first chart's claimant. Each chart now needs a claimant line after
    the chart before it."""
    payload = invented_nevada_with("") + (
        f"{line}<table>{INVENTED_HEADER}</table>".encode()
    )
    with pytest.raises(TableStructureError, match="lacks state or claimant"):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    "line", ["<h4>Couple</h4>", "<h4>Couple<sup>1</sup></h4>"]
)
def test_invented_charts_each_after_a_claimant_line_read_their_own(line):
    """The round-8 review's ``Couple<sup>1</sup>`` reads as a couple line now
    that footnote markers are dropped for recognition."""
    payload = invented_nevada_with("") + (
        f"{line}<table>{INVENTED_HEADER}</table>".encode()
    )
    contexts = describe_poms_tables(payload)
    assert [c["claimant_type"] for c in contexts] == ["individual", "couple"]


@pytest.mark.parametrize(
    "line",
    [
        "Utah payment levels effective January 1, 2031",
        "Payment levels effective January 1, 2031 for Utah",
        "Effective January 1, 2031 for Washington DC",
        "Washington, D.C. Effective January 1, 2031",
        "Utah (UT) Effective January 1, 2031",
    ],
)
def test_invented_effective_line_naming_another_state_is_refused(line):
    """Regression: an effective-date sentence that dated another State in a
    form other than "State Effective" carried that date into this section."""
    with pytest.raises(TableStructureError, match="section heading"):
        describe_poms_tables(invented_nevada_with(f"<p>{line}</p>"))


def test_invented_effective_line_before_any_state_heading_is_not_refused():
    """Before the first State heading no section is open, and the heading
    that opens one sets its own date."""
    payload = invented_nevada_with(
        "", before="<p>Payment levels effective January 1, 2031 for Utah</p>"
    )
    assert invented_selector(payload) == (
        "Nevada",
        "individual",
        "2030-01-01",
        [0],
    )


@pytest.mark.parametrize(
    "line",
    [
        "Nevada payment levels effective January 1, 2031",
        "Nevada (NV) Effective January 1, 2031",
    ],
)
def test_invented_effective_line_naming_its_own_state_is_read(line):
    payload = invented_nevada_with(f"<p>{line}</p>")
    assert invented_selector(payload) == (
        "Nevada",
        "individual",
        "2031-01-01",
        [0],
    )


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        (
            "<h3>U<span>tah</span></h3><h4>Individual</h4>",
            ("Utah", "individual", None, []),
        ),
        (
            "<h4>Cou<span>ple</span></h4>",
            ("Nevada", "couple", "2030-01-01", [0]),
        ),
    ],
    ids=["state_heading", "claimant_heading"],
)
def test_invented_inline_markup_inside_a_word_keeps_the_word(
    fragment, expected
):
    """Regression: a space at each inline element's edge split "Utah" and
    "Couple", keeping Nevada's definitions and claimant."""
    assert invented_selector(invented_nevada_with(fragment)) == expected


@pytest.mark.parametrize(
    "block",
    [
        "<h3>Invented note<br>New York (NJ)</h3>",
        "<h4>Invented note<br>Description of supplements for Utah (NV)</h4>",
        "<p>New York (NJ)</p>",
        "<p>New York<sup>1</sup> (NJ)</p>",
    ],
)
def test_invented_state_heading_line_with_another_code_is_refused(block):
    """Regression: a later line shaped as a State heading, with a postal
    code that is not that State's, kept Nevada's selector."""
    with pytest.raises(TableStructureError, match="does not head"):
        describe_poms_tables(invented_nevada_with(block))


def test_invented_later_state_heading_line_with_its_own_code_heads():
    payload = invented_nevada_with(
        "<h3>Invented note<br>New Jersey (NJ)</h3><h4>Individual</h4>"
    )
    assert invented_selector(payload) == (
        "New Jersey",
        "individual",
        None,
        [],
    )


@pytest.mark.parametrize(
    "heading",
    [
        # The round-8 review's A1, its supplement-heading form and its
        # footnote-link form.
        "<h3>Utah<sup>1</sup></h3>",
        "<h3>Description of supplements for Utah<sup>1</sup></h3>",
        "<h3>Utah<a href='#fn1'>1</a></h3>",
        "<h3>Description of supplements for Utah<a href='#fn2'>2</a></h3>",
        "<h3><sup>1</sup>Utah</h3>",
        "<h3>Utah<sup><b>1</b></sup></h3>",
    ],
)
def test_invented_footnote_marker_after_a_state_name_heads_it(heading):
    """Regression: a footnote marker glued to a State's name hid it, so
    Nevada's definitions charted Utah. Footnote markers are dropped when a
    heading is recognized, as they are from table cells."""
    payload = invented_nevada_with(heading + "<h4>Individual</h4>")
    assert invented_selector(payload) == ("Utah", "individual", None, [])


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        # A4: rendered, the words run together, so the heading names Utah
        # but heads nothing.
        (
            "<h3><b>Description of supplements for</b>Utah</h3>"
            "<h4>Individual</h4>",
            "does not head",
        ),
        # The same heading in a paragraph, which no heading net reads.
        (
            "<p><b>Description of supplements for</b>Utah</p>"
            "<h4>Individual</h4>",
            "does not head",
        ),
        # B1.
        ("<p>Couple for Utah<sup>1</sup></p>", "names another State"),
        ("<p>Couple for Utah<a href='#fn1'>1</a></p>", "names another State"),
        # C1 and its trailing form.
        (
            "<p>Utah<sup>1</sup> payment levels effective January 1, 2031</p>",
            "section heading",
        ),
        (
            "<p>Payment levels effective January 1, 2031 for Utah<sup>2</sup>"
            "</p>",
            "section heading",
        ),
        # D1: hidden text glued to the name.
        ("<h3>Utah<span hidden>x</span></h3>", "does not head"),
        ("<h4>Invented note<br>Utah<b>x</b></h4>", "does not head"),
        # A claimant line only the spaced reading shows.
        ("<p><b>Couple</b>for Nevada</p>", "inline elements spaced"),
    ],
)
def test_invented_state_name_glued_across_an_inline_edge_is_refused(
    fragment, message
):
    """Regression: a State name glued to the text of the element beside it
    became another word, so no State net saw it and Nevada's selector
    charted the block. Every net now also reads each line with a space at
    every element's edge."""
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(fragment))


GLUED_NAMES = [(name, name) for name in _STATES if name != "Nevada"] + [
    ("Washington, D.C.", "District of Columbia"),
    ("Hawai&#699;i", "Hawaii"),
]
GLUED_CONTEXTS = [
    "<h3>{name}</h3><h4>Individual</h4>",
    "<h3>Description of supplements for {name}</h3><h4>Individual</h4>",
    "<h4>Invented note<br>{name}</h4>",
    "<p>Couple for {name}</p>",
    "<p>{name} payment levels effective January 1, 2031</p>",
    "<p>Payment levels effective January 1, 2031 for {name}</p>",
    "<p>{name} Effective January 1, 2031</p>",
]


def invented_nevada_outcome(fragment: str):
    """The last chart's State, or None when the page refuses."""
    try:
        selectors = describe_poms_tables(invented_nevada_with(fragment))
    except TableStructureError:
        return None
    return selectors[-1]["state"]


@settings(deadline=None, max_examples=150)
@given(
    st.sampled_from(GLUED_NAMES),
    st.sampled_from(["<sup>{w}</sup>", "<a href='#fn{w}'>{w}</a>"]),
    st.booleans(),
    st.text("0123456789x", min_size=1, max_size=3),
    st.sampled_from(GLUED_CONTEXTS),
)
def test_invented_footnote_marker_on_a_state_name_never_charts_nevada(
    named, marker, before, word, context
):
    """Property: a footnote marker touching a State's name, on either side,
    in a heading, claimant line or date sentence of Nevada's section,
    leaves that block read as without the marker: it reads that State's
    section or refuses, and never charts under Nevada's selector."""
    text, name = named
    piece = marker.format(w=word)
    glued = piece + text if before else text + piece
    assert invented_nevada_outcome(context.format(name=glued)) in {name, None}


@settings(deadline=None, max_examples=150)
@given(
    st.sampled_from(GLUED_NAMES),
    st.sampled_from(
        [
            "<sup>{w}</sup>",
            "<a href='#fn{w}'>{w}</a>",
            "<span hidden>{w}</span>",
            "<b>{w}</b>",
            "<span>{w}</span>",
        ]
    ),
    st.booleans(),
    st.text("0123456789x", min_size=1, max_size=3),
    st.sampled_from(GLUED_CONTEXTS),
)
def test_invented_inline_edge_hides_no_state_from_a_net(
    named, glue, before, word, context
):
    """Property: an inline element glued to a State's name hides that
    State from no net. Whenever the page with a space at the glued edge
    refuses or reads that State, the glued page refuses or reads it too.
    (The space-separated page may read as prose: "x Utah Effective" is no
    date sentence.)"""
    text, name = named
    piece = glue.format(w=word)
    glued = piece + text if before else text + piece
    spaced = piece + " " + text if before else text + " " + piece
    if invented_nevada_outcome(context.format(name=spaced)) in {name, None}:
        assert invented_nevada_outcome(context.format(name=glued)) in {
            name,
            None,
        }


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        # R1: only a line of the block, not its whole text, is an
        # effective-date sentence.
        (
            "<p>Utah payment levels effective January 1, 2031"
            + INVENTED_FILLER
            + "</p>",
            "section heading",
        ),
        # R3: no space before the code, in a block that is no heading.
        ("<p>New York(NJ)</p>", "does not head"),
        ("<p>Invented note<br>New York(NJ)</p>", "does not head"),
        # R5: only the whole text is a claimant line.
        ("<p>Couple for<br>Utah residents</p>", "names another State"),
    ],
    ids=["R1", "R3", "R3_line", "R5"],
)
def test_invented_round_8_mutant_witnesses_are_refused(fragment, message):
    """The round-8 review's R1, R3 and R5 mutants each read one of these
    pages silently; each now fails this test."""
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_long_state_date_line_with_a_footnote_is_refused():
    """A line too long to be an effective-date sentence that still opens
    as another State's date line, once its footnote marker is dropped,
    refuses: that State's section heading was not read."""
    payload = invented_nevada_with(
        "<p>Utah<sup>1</sup> Effective January 1, 2031 "
        + "Invented filler " * 30
        + "</p>"
    )
    with pytest.raises(TableStructureError, match="section heading"):
        describe_poms_tables(payload)


def test_invented_footnote_marker_glued_to_effective_starts_no_date():
    """The date sentence is read from the joined text, footnote markers
    and all, so "Effective" with a marker glued to it starts no date
    sentence and the section's date stands. One pinned page holds such a
    paragraph; reading its bare text would move that page's chart date."""
    payload = invented_nevada_with("<p>Effective<sup>1</sup> invented</p>")
    assert invented_selector(payload) == (
        "Nevada",
        "individual",
        "2030-01-01",
        [0],
    )


@pytest.mark.parametrize(
    "line",
    [
        "Couple for Washington, D.C.",
        "Couple for Washington,DC",
        "Couple for washington dc",
    ],
)
def test_invented_district_claimant_line_names_its_own_section(line):
    """A claimant line naming the District, by any alias, names no other
    State in the District's section, Washington State included."""
    payload = invented_payload(
        "<h3>Washington, D.C.</h3>"
        + invented_definitions([("A", "Invented District definition")])
        + "<p>Monthly payment levels effective January 1, 2030</p>"
        + f"<p>{line}</p><table>{INVENTED_HEADER}</table>"
    )
    assert invented_selector(payload) == (
        "District of Columbia",
        "couple",
        "2030-01-01",
        [0],
    )


def invented_washington_with(fragment: str) -> bytes:
    """Washington State's section, then ``fragment`` and a chart."""
    return invented_payload(
        "<h3>Washington</h3>"
        + invented_definitions([("A", "Invented Washington definition")])
        + "<p>Monthly payment levels effective January 1, 2030</p>"
        "<h4>Individual</h4>" + fragment + f"<table>{INVENTED_HEADER}</table>"
    )


@pytest.mark.parametrize(
    "heading", ["Washington,DC", "Washington,D.C.", "Washington D.C."]
)
def test_invented_district_heading_without_a_space_heads_the_district(
    heading,
):
    """Regression: in Washington State's section, "Washington,DC" heads
    nothing, so the chart kept Washington's definitions."""
    payload = invented_washington_with(
        f"<h3>{heading}</h3><h4>Individual</h4>"
    )
    assert invented_selector(payload) == (
        "District of Columbia",
        "individual",
        None,
        [],
    )


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        ("<p>Couple for Washington,D.C.</p>", "names another State"),
        (
            "<p>Washington,D.C. Effective January 1, 2031</p>",
            "section heading",
        ),
    ],
)
def test_invented_district_line_in_washington_section_is_refused(
    fragment, message
):
    """Regression: these lines passed in Washington State's section, the
    date carrying the District's date into Washington's chart."""
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_washington_with(fragment))


@pytest.mark.parametrize(
    "heading",
    [
        "U&shy;tah",
        "Ut&#8203;ah",
        "&#xfeff;Utah",
        "Hawai&#699;i",
        "Hawai'i",
        "Hawai&#8216;i",
        "Hawai&#8217;i",
        "Description of supplements &ndash; Utah",
        "Description of supplements&mdash;Utah",
        "Procedure &#8722; Utah",
    ],
)
def test_invented_heading_name_forms_head_their_state(heading):
    """Regression: a soft hyphen or other format character in a State's
    name, the okina in "Hawaiʻi" and a dash other than a hyphen after a
    heading's prefix each kept Nevada's selector."""
    name = "Hawaii" if "Hawai" in heading else "Utah"
    payload = invented_nevada_with(f"<h3>{heading}</h3><h4>Individual</h4>")
    assert invented_selector(payload) == (name, "individual", None, [])


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        ("<p>Couple for U&shy;tah</p>", "names another State"),
        ("<h3>&#8288;<br>Utah residents</h3>", "does not head"),
        # A postal code in parentheses names its State.
        (
            "<p>Payment levels effective January 1, 2031 (UT)</p>",
            "section heading",
        ),
        ("<p>Couple for residents (ut)</p>", "names another State"),
        # So do an upper-case code standing as a word and an abbreviation.
        (
            "<p>Payment levels effective January 1, 2031 for UT</p>",
            "section heading",
        ),
        ("<p>Couple for N.J.</p>", "names another State"),
        ("<p>Couple for Calif.</p>", "names another State"),
        ("<h4>Invented note<br>Pa. notes</h4>", "does not head"),
        ("<p>Couple for D.C.</p>", "names another State"),
        (
            "<p>Payment levels effective January 1, 2031 for N. Y.</p>",
            "section heading",
        ),
        ("<h4>Invented note<br>R.I. notes</h4>", "does not head"),
    ],
)
def test_invented_other_name_forms_are_netted(fragment, message):
    """Regression: each of these named another State in Nevada's section
    and passed every net."""
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    "fragment",
    [
        "<h3>N.J.</h3><h4>Individual</h4>",
        "<h3>Mich.</h3><h4>Individual</h4>",
        "<h3>(UT)</h3><h4>Individual</h4>",
        "<h3>UT</h3><h4>Individual</h4>",
    ],
)
def test_invented_abbreviation_or_code_alone_heads_nothing(fragment):
    """An abbreviation or a postal code alone names a State to the nets but
    heads no section, so the block refuses rather than heads one."""
    with pytest.raises(TableStructureError, match="does not head"):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_format_characters_are_unicode_category_cf():
    """The pinned format characters are exactly Unicode's Cf category as
    this interpreter's unicodedata has it (Unicode 15.1 on 3.13, 16.0 on
    3.14, which agree on Cf)."""
    pinned = {
        point
        for point in range(sys.maxunicode + 1)
        if _blank("a" + chr(point) + "a") == "aa"
    }
    category = {
        point
        for point in range(sys.maxunicode + 1)
        if unicodedata.category(chr(point)) == "Cf"
    }
    assert pinned == category


def test_invented_deeply_nested_chart_cell_reads_without_recursion():
    """Regression: copying a chart whose cell nests 50,000 spans crashed the
    interpreter (exit 139), so the read runs in its own process."""
    program = (
        "from populace_dynamics.income_resources.aggregate_poms import "
        "_payment_rows\n"
        "from populace_dynamics.income_resources.aggregate_tables import "
        "parse_html\n"
        "depth = 50_000\n"
        "page = ('<table><tr><td>A</td><td>' + '<span>' * depth + '100' "
        "+ '</span>' * depth + '</td></tr></table>')\n"
        "rows = _payment_rows(parse_html(page).find('.//table'))\n"
        "print(len(rows), [token.text for token in rows[0]])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "1 ['A', '100']"


def test_invented_table_nested_in_a_chart_cell_adds_no_rows():
    """A table inside a chart cell is that cell's text, as the copy before
    the skeleton read it; its rows are not the chart's."""
    page = (
        "<table><tr><td>A</td><td><p>100</p><table>"
        "<tr><td>w1</td><td>w2</td></tr><tr><td>w3</td></tr></table>"
        "</td></tr><tr><td>B</td><td>200</td></tr></table>"
    )
    rows = _payment_rows(parse_html(page).find(".//table"))
    assert [[token.text for token in row] for row in rows] == [
        ["A", "100 w1 w2 w3"],
        ["B", "200"],
    ]


def invented_tables(html: str):
    """Each table's caption text and its rows' cell texts, in order."""
    root = parse_html(html)
    pending, out = [root], []
    while pending:
        node = pending.pop()
        pending.extend(list(node)[::-1])
        if node.tag == "table":
            caption = node.find("caption")
            out.append(
                (
                    normalized_text(caption) if caption is not None else None,
                    [
                        [
                            normalized_text(c)
                            for c in row
                            if c.tag in {"td", "th"}
                        ]
                        for row in node.iter("tr")
                    ],
                )
            )
    return out


# Each page's expected tables are what html5lib 1.1 builds for it.
@pytest.mark.parametrize(
    ("html", "expected"),
    [
        pytest.param(
            "<table><tr><td>w1<table><tr><td>w2<tbody><tr><td>w3</table>w4"
            "</td><td>w5</table>",
            [
                (None, [["w1 w2 w3 w4", "w5"], ["w2"], ["w3"]]),
                (None, [["w2"], ["w3"]]),
            ],
            id="section_start_in_a_nested_table_cell",
        ),
        pytest.param(
            "<table><caption><table><tr><td>w1</table>w2</caption>"
            "<tr><td>w3</table>",
            [("w1 w2", [["w1"], ["w3"]]), (None, [["w1"]])],
            id="caption_holding_a_table",
        ),
        pytest.param(
            "<table><caption>w0<table><tr><td>w1</table>w2<tr><td>w3</table>",
            [("w0 w1 w2", [["w1"], ["w3"]]), (None, [["w1"]])],
            id="row_start_ends_a_caption_after_its_nested_table",
        ),
        pytest.param(
            "<table><tr><td>w1<colgroup><col></colgroup><td>w2</table>",
            [(None, [["w1"], ["w2"]])],
            id="colgroup_start_in_a_cell",
        ),
        pytest.param(
            "<table><tr><td>w9<td>w10<col><td>w11</table>",
            [(None, [["w9", "w10"], ["w11"]])],
            id="col_start_in_a_cell",
        ),
        pytest.param(
            "<table><colgroup><col><td>w1</table>",
            [(None, [["w1"]])],
            id="cell_start_ends_an_open_colgroup",
        ),
        pytest.param(
            "<table><tr><td>w1<tbody><td>w2</table>",
            [(None, [["w1"], ["w2"]])],
            id="cell_after_a_section_start_implies_a_row",
        ),
        pytest.param(
            "<table><td>w1<td>w2</table>",
            [(None, [["w1", "w2"]])],
            id="cell_directly_in_a_table_implies_a_row",
        ),
        pytest.param(
            "<table><tr><td>w1</td></tr><table><tr><td>w2</table>",
            [(None, [["w1"]]), (None, [["w2"]])],
            id="table_start_in_a_table_ends_it",
        ),
        pytest.param(
            "<table><td></tbody>w0<tr><td>w1</table>",
            [(None, [[""], ["w1"]])],
            id="section_end_tag_closes_the_implied_tbody",
        ),
        pytest.param(
            "<div><table><tr><td>w1</div>w2<td>w3</table>",
            [(None, [["w1w2", "w3"]])],
            id="block_end_tag_stops_at_the_cell",
        ),
        pytest.param(
            "<table><tr><td><table><tr><td>w1</tr></td>w2</table>w3<td>w4"
            "</table>",
            [(None, [["w1 w2 w3", "w4"], ["w1"]]), (None, [["w1"]])],
            id="row_end_tag_stops_at_its_table",
        ),
    ],
)
def test_invented_tree_builds_tables_as_html_does(html, expected):
    """Regression: each page built different tables before these rules."""
    assert invented_tables(html) == expected


def invented_blocks(
    html: str, tags=("p", "h3", "button", "li", "dt", "dd", "div", "object")
):
    root = parse_html(html)
    pending, out = [root], []
    while pending:
        node = pending.pop()
        pending.extend(list(node)[::-1])
        if node.tag in tags and normalized_text(node):
            out.append((node.tag, normalized_text(node)))
    return out


# Each page's expected blocks are what html5lib 1.1 builds for it.
@pytest.mark.parametrize(
    ("html", "expected"),
    [
        pytest.param(
            "<h3><button>w1</h3>w2</button><p>w3</p>",
            [("h3", "w1"), ("button", "w1"), ("p", "w3")],
            id="heading_end_tag_ends_a_button_inside_it",
        ),
        pytest.param(
            "<p><button>w1<button>w2</button>w3</p>",
            [("p", "w1 w2 w3"), ("button", "w1"), ("button", "w2")],
            id="button_start_ends_an_open_button",
        ),
        pytest.param(
            "<h3>w0</p>w1</h3>",
            [("h3", "w0 w1")],
            id="paragraph_end_tag_without_a_paragraph",
        ),
        pytest.param(
            "<ul><li>w0<li>w1<div>w2<li>w3</ul>",
            [("li", "w0"), ("li", "w1 w2"), ("div", "w2"), ("li", "w3")],
            id="list_item_start_ends_the_open_item",
        ),
        pytest.param(
            "<div>w0</body>w1</div>",
            [("div", "w0w1")],
            id="body_end_tag_closes_nothing",
        ),
        pytest.param(
            "<p>w0<span>w1</div>w2</span>w3</p>",
            [("p", "w0 w1w2 w3")],
            id="block_end_tag_without_its_block_is_ignored",
        ),
        pytest.param(
            "<div><span>w0<p>w1</span>w2</p>w3</div>",
            [("div", "w0 w1w2 w3"), ("p", "w1w2")],
            id="inline_end_tag_stops_at_an_open_block",
        ),
        pytest.param(
            "<ul><li>w0<ul><li>w1</ul>w2</ul>",
            [("li", "w0 w1 w2"), ("li", "w1")],
            id="nested_list_item_start_keeps_the_outer_item",
        ),
        pytest.param(
            "<body><div>w0</body>w1</div>",
            [("div", "w0w1")],
            id="body_end_tag_after_a_body_start_closes_nothing",
        ),
        pytest.param(
            "<p>w0<button>w1</p>w2</button>w3",
            [("p", "w0 w1 w2 w3"), ("button", "w1 w2")],
            id="paragraph_end_tag_inside_a_button",
        ),
        pytest.param(
            "<ul><li>w0<ol><span>w1</li>w2</ol></ul>",
            [("li", "w0 w1w2")],
            id="list_item_end_tag_stops_at_a_nested_list",
        ),
        pytest.param(
            "<div>w0<p>w1</div>w2",
            [("div", "w0 w1"), ("p", "w1")],
            id="block_end_tag_closes_its_open_paragraph",
        ),
        pytest.param(
            "<div><object>w0</object>w1</div>",
            [("div", "w0 w1"), ("object", "w0")],
            id="scope_element_end_tag_closes_itself",
        ),
        pytest.param(
            "<ul><li>w0<address>w1<li>w2</ul>",
            [("li", "w0 w1"), ("li", "w2")],
            id="list_item_start_ends_the_item_around_an_address",
        ),
        pytest.param(
            "<dl><dt>w0<dd>w1</dl>",
            [("dt", "w0"), ("dd", "w1")],
            id="dd_start_ends_an_open_dt",
        ),
        pytest.param(
            "<dl><dd>w0<dt>w1</dl>",
            [("dd", "w0"), ("dt", "w1")],
            id="dt_start_ends_an_open_dd",
        ),
        pytest.param(
            "<html><div>w0</html>w1</div>",
            [("div", "w0w1")],
            id="html_end_tag_after_an_html_start_closes_nothing",
        ),
        pytest.param(
            "<div>w0</html>w1</div>",
            [("div", "w0w1")],
            id="html_end_tag_closes_nothing",
        ),
        pytest.param(
            "<p>w0<html>w1</p>w2<h3>w3</h3>",
            [("p", "w0w1"), ("h3", "w3")],
            id="html_start_tag_in_a_paragraph_builds_nothing",
        ),
        pytest.param(
            "<h3>w0<html>w1</h3>w2<h4>w3</h4>",
            [("h3", "w0w1")],
            id="html_start_tag_in_a_heading_builds_nothing",
        ),
        pytest.param(
            "<html><body><div>w0<html>w1</div>w2",
            [("div", "w0w1")],
            id="second_html_start_tag_builds_nothing",
        ),
        pytest.param(
            "<body><noscript><h3>w0</noscript>w1<p>w2",
            [("h3", "w0w1 w2"), ("p", "w2")],
            id="noscript_end_tag_with_a_heading_open_inside_is_ignored",
        ),
        pytest.param(
            "<p>w0<noscript>w1</noscript>w2</p>",
            [("p", "w0 w1 w2")],
            id="noscript_end_tag_closes_its_noscript",
        ),
        pytest.param(
            "<div><caption>w0</caption><colgroup><col>w1</div><p>w2",
            [("div", "w0w1"), ("p", "w2")],
            id="table_part_start_tags_outside_a_table_build_nothing",
        ),
        pytest.param(
            "<p>w0<tbody>w1<thead>w2<tfoot>w3</p>",
            [("p", "w0w1w2w3")],
            id="table_section_start_tags_outside_a_table_build_nothing",
        ),
        pytest.param(
            "<table><tr><td>w0</table><td>w1<p>w2",
            [("p", "w2")],
            id="cell_start_tag_after_a_closed_table_builds_nothing",
        ),
    ],
)
def test_invented_tree_builds_blocks_as_html_does(html, expected):
    assert invented_blocks(html) == expected


def test_invented_later_html_start_tag_adds_only_missing_attributes():
    """As in html5lib 1.1, a later html start tag gives the html element
    the attributes it lacks and changes none it has."""
    root = parse_html('<html lang="w0"><body><p>w1<html lang="w2" dir="w3">')
    (html,) = root.iter("html")
    assert html.attrib == {"lang": "w0", "dir": "w3"}


def test_invented_end_br_is_a_line_break():
    """HTML reads ``</br>`` as ``<br>``."""
    root = parse_html("<p>w0</br>w1</p>")
    assert [child.tag for child in root.find(".//p")] == ["br"]


# Round 9's review: prose, footnote markers and paragraph captions.


def invented_nevada_after(claimant: str, fragment: str) -> bytes:
    """``invented_nevada_with`` with ``claimant`` as its claimant heading."""
    return invented_nevada_with(fragment).replace(
        b"<h4>Individual</h4>", f"<h4>{claimant}</h4>".encode(), 1
    )


# The round-9 review's A1, A2, A3 and A6, each read as its first claimant
# word before round 10, and more prose forms: each holds a claimant word
# and is no claimant line.
PROSE_CLAIMANT_FRAGMENTS = [
    # The opening, and whether it holds both claimant types.
    (
        "Couple",
        "<p>A recipient or couple qualifies if invented conditions hold",
        True,
    ),
    ("Couple", "<p>Invented payments go to an eligible individual", False),
    ("Individual", "<p>Invented payments go to each eligible couple", False),
    ("Couple", "<p>Individual or couple", True),
    # Its list item and "eligibility rules" forms.
    ("Couple", "<ul><li>Invented supplement for the recipient", False),
    ("Couple", "<p>Invented eligibility rules: Individual", False),
    ("Couple", "<div>Invented note<br>Couple or individual notes", True),
    # A claimant word after a date sentence that ends with neither a date
    # nor a State, or after other text that ends with a State.
    (
        "Individual",
        "<p>Payment levels effective January 1, 2030 for each eligible"
        " Couple",
        False,
    ),
    ("Individual", "<p>Invented eligibility rules for Nevada Couple", False),
]


def invented_prose_fragment(opening: str, tail: str) -> str:
    """Close a fragment of PROSE_CLAIMANT_FRAGMENTS after ``tail``."""
    closes = {"<p>": "</p>", "<ul><li>": "</li></ul>", "<div>": "</div>"}
    start = next(tag for tag in closes if opening.startswith(tag))
    return opening + tail + closes[start]


@pytest.mark.parametrize(
    ("claimant", "opening", "two"), PROSE_CLAIMANT_FRAGMENTS
)
def test_invented_prose_mentioning_a_claimant_names_none(
    claimant, opening, two
):
    """Only a claimant line names a chart's claimant: a heading form, or a
    caption after a date. Prose of 80 characters or more that mentions a
    claimant word names none, so the claimant heading before it stands."""
    fragment = invented_prose_fragment(opening, INVENTED_LONG_TAIL)
    assert invented_selector(invented_nevada_after(claimant, fragment)) == (
        "Nevada",
        claimant.lower(),
        "2030-01-01",
        [0],
    )


@pytest.mark.parametrize(
    ("claimant", "opening", "two"), PROSE_CLAIMANT_FRAGMENTS
)
def test_invented_short_prose_mentioning_a_claimant_leaves_it_unread(
    claimant, opening, two
):
    """Regression (the round-10 review's Medium 2): a line under 80
    characters that holds a claimant word but is no claimant line names a
    claimant the reader does not read, so the heading before it no longer
    stands: the chart refuses, and a line that holds both types refuses as
    naming two."""
    fragment = invented_prose_fragment(opening, "")
    message = "two claimants" if two else "lacks state or claimant"
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_after(claimant, fragment))


@pytest.mark.parametrize(
    ("fragment", "date"),
    [
        ("<p>Couple</p>", "2030-01-01"),
        ("<p>b. Couple payment levels for Nevada</p>", "2030-01-01"),
        ("<p>2) Couple Payment Levels for the Nevada (NV)</p>", "2030-01-01"),
        ("<p>Couple payment level or Nevada</p>", "2030-01-01"),
        ("<p>Couple<sup>1</sup></p>", "2030-01-01"),
        ("<p>1)Couple</p>", "2030-01-01"),
        ("<p>Nevada Effective 1/1/2031 Couple</p>", "2031-01-01"),
        (
            "<p>Monthly payment levels effective January 1, 2031 Nevada"
            " Couple</p>",
            "2031-01-01",
        ),
        ("<p>Effective January 1, 2031 Couple</p>", "2031-01-01"),
    ],
)
def test_invented_claimant_line_forms_name_their_claimant(fragment, date):
    """The heading forms, the source's "or" for "for" among them, and the
    date captions name their claimant word."""
    assert invented_selector(invented_nevada_with(fragment)) == (
        "Nevada",
        "couple",
        date,
        [0],
    )


@pytest.mark.parametrize(
    "fragment",
    [
        # Within one claimant line: a caption whose date sentence names the
        # other claimant.
        "<p>Couple payment levels effective January 1, 2030 Individual</p>",
        "<p>Nevada Effective for a couple 1/1/2030 Individual</p>",
        # Across lines, as the review's O3 witness reads now that it is
        # prose.
        "<p>Individual<br>Couple</p>",
        "<p>Couple<br>Recipient for Nevada</p>",
        # A claimant word that only the spaced reading shows.
        "<p>Payment levels effective for<b>couple</b>s January 1, 2030"
        " Individual</p>",
    ],
)
def test_invented_claimant_lines_naming_two_types_are_refused(fragment):
    """A block names at most one claimant type: every claimant word of a
    claimant line counts, in every reading, across the block's lines."""
    with pytest.raises(TableStructureError, match="two claimants"):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    "fragment",
    [
        "<p>A recipient or couple in Utah qualifies</p>",
        "<p>Invented payments go to an individual or couple in UT</p>",
    ],
)
def test_invented_prose_mentioning_a_claimant_is_still_guarded(fragment):
    """Prose that mentions a claimant names none, but may name no State
    other than the section's."""
    with pytest.raises(TableStructureError, match="names another State"):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    ("date", "message"),
    [
        # The review's B1 and B2: the marker joins the day.
        ("January 1<sup>2</sup>, 2031", "reads differently"),
        ("January 1<a href='#fn5'>5</a>, 2031", "reads differently"),
        # A date range and markers after the year or between month and day.
        (
            "from January 1<sup>3</sup>, 2031 to June 30, 2031",
            "reads differently",
        ),
        ("January 1, 2031<sup>1</sup>", "reads differently"),
        ("1/1/2031<sup>2</sup>", "reads differently"),
        ("January<sup>1</sup> 2, 2031", "reads differently"),
        # A marker inside "from" hides the range the bare reading states.
        (
            "fr<sup>1</sup>om March 1, 2031 to June 30, 2031",
            "reads differently",
        ),
    ],
)
def test_invented_footnote_marker_inside_a_date_is_refused(date, message):
    """Regression: the date sentence was read joined only, so a marker
    inside it changed or hid its date silently."""
    payload = invented_nevada_with("").replace(
        b"effective January 1, 2030", f"effective {date}".encode(), 1
    )
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    "line",
    [
        # The review's B3 and B4: only the bare reading is a sentence.
        "Effective<sup>1</sup> January 1, 2031",
        "Nevada<sup>1</sup> Effective January 1, 2031",
        "Payment levels effec<sup>2</sup>tive January 1, 2031",
        # And a State date line with a marker on its day.
        "Nevada Effective January 1<sup>4</sup>, 2031",
    ],
)
def test_invented_footnote_marker_inside_a_date_sentence_is_refused(line):
    """Regression: a marker inside "Effective" or after a State's name hid
    the sentence, and the section's earlier date stood."""
    with pytest.raises(TableStructureError, match="footnote markers"):
        describe_poms_tables(invented_nevada_with(f"<p>{line}</p>"))


@pytest.mark.parametrize(
    "body",
    [
        # The review's N1, and its link-marker form.
        "<p><sup>1</sup>Effective February 1, 2031.</p>",
        "<p><a href='#fn1'>1</a>Effective February 1, 2031.</p>",
        "<p><sup>2</sup> Effective 2/2031, as the invented note says.</p>",
        # Round 11's R15 witness, and its sentence form: a marker only the
        # table cells' rule counts, a link to a footnote on another page.
        "<p><a href='0501415010#fn1'>1</a>Revised March 1, 2031</p>",
        "<p><a href='0501415010#fn2'>2</a>Effective February 1, 2031.</p>",
    ],
)
def test_invented_footnote_body_between_charts_keeps_the_date(body):
    """A footnote body that opens with its marker, by either marker rule, is
    no date sentence, as in one pinned page between two charts, so the
    section's date stands."""
    payload = invented_nevada_with("") + (
        f"{body}<h4>Couple</h4><table>{INVENTED_HEADER}</table>".encode()
    )
    *_, last = describe_poms_tables(payload)
    assert (last["state"], last["claimant_type"], last["effective_from"]) == (
        "Nevada",
        "couple",
        "2030-01-01",
    )


@settings(deadline=None, max_examples=200)
@given(
    st.sampled_from(
        [
            ("Monthly payment levels effective January 1, 2031", "2031-01-01"),
            ("Payment levels effective 3/1/2031", "2031-03-01"),
            (
                "Payment levels effective from March 1, 2031 to June 30, 2031",
                "2031-03-01",
            ),
            ("Nevada Effective 7/1/31", "2031-07-01"),
        ]
    ),
    st.lists(
        st.tuples(
            st.sampled_from(
                [
                    "<sup>{w}</sup>",
                    "<a href='#fn{w}'>{w}</a>",
                    "<a href='x.html#fn{w}'>{w}</a>",
                ]
            ),
            st.text("0123456789x*", min_size=1, max_size=3),
            st.floats(0, 1),
        ),
        min_size=1,
        max_size=4,
    ),
)
def test_invented_footnote_marker_never_changes_a_date(sentence, markers):
    """Property (the round-10 review's Low 4): one to four footnote markers,
    by either marker rule, anywhere in an effective-date sentence leave its
    date as it is or refuse. Only markers that all lead the line make it a
    footnote body, which dates nothing, so the section's earlier date
    stands."""
    text, expected = sentence
    cuts = sorted(int(at * len(text)) for _, _, at in markers)
    pieces, last = [], 0
    for (marker, w, _), at in zip(markers, cuts, strict=True):
        pieces += [text[last:at], marker.format(w=w)]
        last = at
    line = "".join(pieces) + text[last:]
    try:
        selector = invented_selector(invented_nevada_with(f"<p>{line}</p>"))
    except TableStructureError:
        return
    if all(at == 0 for at in cuts) and text.startswith("Nevada"):
        assert selector[2] == "2030-01-01"
    else:
        assert selector[2] == expected


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        # The review's C1 and C3: a link elsewhere is text, so the bare
        # reading keeps it and names no State heading or claimant. Each is
        # a short line, so since round 11 C1 refuses as naming another
        # State, and C3 names a claimant the reader does not read; read
        # without the link, C1 would head Utah and C3 name an individual.
        (
            "<p><a href='https://www.fns.usda.gov/invented'>Invented note"
            " on</a> Utah</p><h4>Individual</h4>",
            "short line names another State",
        ),
        (
            "<h4>Couple</h4><p>Individual <a"
            " href='https://www.fns.usda.gov/invented'>invented note</a></p>",
            "lacks state or claimant",
        ),
        # The control.
        (
            "<p>Invented note on Utah</p>",
            "short line names another State",
        ),
        # C2 and C2b: a long sup and a link elsewhere no longer vanish, so
        # the paragraph heads nothing; it opens as Utah's caption, so the
        # caption net refuses it.
        (
            "<p>Utah<sup> invented note</sup></p><h4>Individual</h4>",
            "another State's caption",
        ),
        (
            "<p>Utah <a href='/x/fn-guide'>see guide</a></p><h4>Couple</h4>",
            "another State's caption",
        ),
    ],
    ids=["C1", "C3", "control", "C2", "C2b"],
)
def test_invented_only_short_markers_leave_the_bare_reading(
    fragment, expected
):
    """Regression: any sup, and any link whose href held "fn", was dropped
    from the bare reading, so prose became Utah's heading or a claimant
    line, and Nevada's chart read as Utah's."""
    payload = invented_nevada_with(fragment)
    if isinstance(expected, str):
        with pytest.raises(TableStructureError, match=expected):
            describe_poms_tables(payload)
    else:
        assert invented_selector(payload) == expected


@pytest.mark.parametrize(
    ("block", "bare"),
    [
        ("<p>Utah<sup>1</sup></p>", "Utah"),
        ("<p>Utah<a href='#fn2'>2</a></p>", "Utah"),
        ("<p>Utah<a href='#note'>&#8224;</a></p>", "Utah"),
        ("<p>Utah<sup>*</sup></p>", "Utah"),
        ("<p>Utah<sup><b>1</b></sup></p>", "Utah"),
        ("<p>Utah<sup>1&#8203;</sup></p>", "Utah"),
        ("<p>Utah<sup>1234</sup></p>", "Utah1234"),
        ("<p>Utah<sup>1<b>2345</b></sup></p>", "Utah12345"),
        ("<p>Utah<sup>1 2</sup></p>", "Utah1 2"),
        ("<p>Utah<sup> invented note</sup></p>", "Utah invented note"),
        ("<p>Utah <a href='/x/fn-guide'>see guide</a></p>", "Utah see guide"),
        ("<p>Utah<a href='https://example.invalid/#fn1'>1</a></p>", "Utah1"),
    ],
)
def test_invented_bare_reading_drops_only_footnote_markers(block, bare):
    """A footnote marker in a block's line is a sup, or a link to an anchor
    on the page, holding one to three word characters or footnote signs;
    the bare reading drops only that."""
    element = next(iter(parse_html(block).iter("p")))
    ((_, reading, _),) = _line_renderings(element)
    assert reading == bare


def test_invented_deeply_nested_markers_read_without_recursion():
    depth = 1500
    for inner, heads in (("1", True), ("1234", False)):
        heading = (
            "<h3>Description of supplements for Utah"
            + "<sup>" * depth
            + inner
            + "</sup>" * depth
            + "</h3><h4>Individual</h4>"
        )
        outcome = invented_nevada_outcome(heading)
        assert outcome == ("Utah" if heads else None)


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        # The review's O1 witness, and one whose marker the bare reading
        # drops: only the spaced reading shows the code.
        ("<p>Couple for Nevada<sup>Utah</sup></p>", "names another State"),
        ("<p>Couple for Nevada<sup>UT</sup></p>", "names another State"),
        # O2: only the whole text, read bare, names Utah.
        ("<p>Couple for<br>Utah<sup>1</sup> residents</p>", "names another"),
        # O4: only the bare whole text is a State date line, a footnote
        # body that opens with its marker; its next line, shaped as Utah's
        # heading, heads nothing.
        (
            "<p><sup>1</sup>Utah Effective January 1, 2031<br>Utah</p>"
            "<h4>Couple</h4>",
            "section heading",
        ),
    ],
    ids=["O1", "O1_marker", "O2", "O4"],
)
def test_invented_round_9_mutant_witnesses_are_refused(fragment, message):
    """The round-9 review's O1, O2 and O4 mutants each read one of these
    pages silently; each now fails this test."""
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    "word", sorted(code.lower() for code in _POSTAL_CODES.values())
)
def test_invented_lower_case_two_letter_word_names_no_state(word):
    """The review's O6: a lower-case word that spells a postal code, as in
    "de facto", names no State, in prose that mentions a claimant or in a
    date sentence; the upper-case code does."""
    prose = (
        f"<p>Couple payment levels for Nevada {word} facto"
        f"{INVENTED_LONG_TAIL}</p>"
    )
    assert invented_selector(invented_nevada_with(prose))[:2] == (
        "Nevada",
        "individual",
    )
    sentence = f"<p>Payment levels effective January 1, 2031 {word} facto</p>"
    assert invented_selector(invented_nevada_with(sentence))[2] == "2031-01-01"
    if word != "nv":
        with pytest.raises(TableStructureError, match="names another"):
            describe_poms_tables(invented_nevada_with(prose.upper()))


CAPTION_FORMS = [
    "{name} (continued)",
    "State of {name}",
    "{name} <small>(Invented)</small>",
    "Description of supplements - {name} (invented)",
    "B. {name}: invented note",
]


@pytest.mark.parametrize("form", CAPTION_FORMS)
@pytest.mark.parametrize(
    "block", ["<p>{}</p>", "<div>{}</div>", "<ul><li>{}</ul>", "<h5>{}</h5>"]
)
def test_invented_short_caption_of_another_state_is_refused(form, block):
    """Regression (the review's E1): a paragraph caption naming another
    State, which only the h1-h6 net read, charted Nevada's selector. A
    heading keeps the heading net's message."""
    caption = block.format(form.format(name="Utah"))
    message = (
        "heading names a State it does not head"
        if "<h5>" in block
        else "another State's caption"
    )
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(caption + "<p>Couple</p>"))


@settings(deadline=None, max_examples=200)
@given(
    st.sampled_from(GLUED_NAMES + [("utah", "Utah"), ("NEW JERSEY", "")]),
    st.sampled_from(CAPTION_FORMS),
    st.sampled_from(INVENTED_BLOCK_KINDS),
)
def test_invented_short_caption_never_charts_nevada(named, form, kind):
    """Property: a short line that opens as another State's caption, in a
    block of any kind, never charts under Nevada's selector."""
    text, _ = named
    caption = invented_block("p", form.format(name=text), kind, False)
    assert invented_nevada_outcome(caption + "<p>Couple</p>") is None


@pytest.mark.parametrize(
    "caption",
    [
        "<p>N.J. (continued)</p>",
        "<p>UT (continued)</p>",
        "<p>Calif. notes</p>",
        "<p>Hawai&#699;i (continued)</p>",
        "<p>utah (continued)</p>",
        "<p>Washington, D.C. (continued)</p>",
        # A block HTML keeps inside a heading left open, after its chart,
        # is no heading text, and the net reads it.
        "<h4>Individual<table><tr><td>Invented</td></tr></table>"
        "<p>Utah (continued)</p>",
    ],
)
def test_invented_caption_name_forms_are_netted(caption):
    with pytest.raises(TableStructureError, match="another State's caption"):
        describe_poms_tables(invented_nevada_with(caption + "<p>Couple</p>"))


@pytest.mark.parametrize(
    "fragment",
    [
        # The section's own State.
        "<p>Nevada (continued)</p>",
        "<p>State of Nevada</p>",
        # Another State in a line of 80 characters or more, at its start
        # or not. A short line that names it anywhere refuses (the
        # short-line State net).
        f"<p>Invented note on Utah{INVENTED_LONG_TAIL}</p>",
        "<p>Utah " + "invented " * 9 + "note</p>",
        # A lower-case word that spells a postal code.
        "<p>ut infra, invented note</p>",
    ],
)
def test_invented_caption_net_admits_other_lines(fragment):
    assert invented_selector(
        invented_nevada_with(fragment + "<p>Couple</p>")
    ) == ("Nevada", "couple", "2030-01-01", [0])


def test_invented_caption_net_reads_the_district_alias_first():
    """ "Washington, D.C." opens as the District's caption, so it passes in
    the District's section and refuses in Washington State's."""
    district = invented_payload(
        "<h3>District of Columbia</h3>"
        + invented_definitions([("A", "Invented District definition")])
        + "<p>Monthly payment levels effective January 1, 2030</p>"
        + "<p>Washington, D.C. (continued)</p><p>Couple</p>"
        + f"<table>{INVENTED_HEADER}</table>"
    )
    assert invented_selector(district)[:2] == (
        "District of Columbia",
        "couple",
    )
    with pytest.raises(TableStructureError, match="another State's caption"):
        describe_poms_tables(
            invented_washington_with(
                "<p>Washington, D.C. (continued)</p><p>Couple</p>"
            )
        )
    washington = invented_washington_with(
        "<p>Washington (continued)</p><p>Couple</p>"
    )
    assert invented_selector(washington)[:2] == ("Washington", "couple")


def test_invented_caption_before_any_state_heading_is_not_refused():
    """Before the first State heading no section is open; the heading that
    opens one is read as before."""
    payload = invented_nevada_with("", before="<p>Utah (continued)</p>")
    assert invented_selector(payload) == (
        "Nevada",
        "individual",
        "2030-01-01",
        [0],
    )


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        (
            "<h3>Ut<style>.x{}</style>ah</h3><h4>Individual</h4>",
            ("Utah", "individual", None, []),
        ),
        (
            "<h4>Cou<script>invented()</script>ple</h4>",
            ("Nevada", "couple", "2030-01-01", [0]),
        ),
        (
            "<p>Couple for Nevada<script>'Utah'</script></p>",
            ("Nevada", "couple", "2030-01-01", [0]),
        ),
        (
            "<p>Utah<script>invented()</script> Effective January 1, 2031</p>",
            "section heading",
        ),
    ],
)
def test_invented_script_and_style_text_is_not_read(fragment, expected):
    """HTML renders no script or style text, so no reading holds it: the
    text around it joins, as HTML renders it."""
    payload = invented_nevada_with(fragment)
    if isinstance(expected, str):
        with pytest.raises(TableStructureError, match=expected):
            describe_poms_tables(payload)
    else:
        assert invented_selector(payload) == expected


# The round-10 differential's tree gaps. Expected values are html5lib 1.1's.


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        (
            'w0<p>w1<html lang="w2" dir="w3"><html lang="w4">',
            {"lang": "w2", "dir": "w3"},
        ),
        ('<p>w0</p><div><html lang="w2"></div>', {"lang": "w2"}),
        ("<p>w0<html>", {}),
    ],
)
def test_invented_later_html_start_tag_on_an_implied_html_element(
    page, expected
):
    """A page that opens with other content implies its html element, and a
    later html start tag gives it the attributes it lacks; the document
    root stands for it, as no html element is built."""
    root = parse_html(page)
    assert root.find("html") is None
    assert root.attrib == expected


@pytest.mark.parametrize(
    ("page", "tag", "text"),
    [
        ("<pre>\nw0</pre>", "pre", "w0"),
        ("<listing>\nw0</listing>", "listing", "w0"),
        ("<textarea>\nw0</textarea>", "textarea", "w0"),
        ("<pre>\n\nw0</pre>", "pre", "\nw0"),
        ("<pre>w0\n</pre>", "pre", "w0\n"),
        ("<pre>\r\nw0</pre>", "pre", "w0"),
        ("<TEXTAREA>\n<b>w0</b></TEXTAREA>", "textarea", "<b>w0</b>"),
        ("<p>w0<textarea>\nw1</textarea>w2", "textarea", "w1"),
    ],
)
def test_invented_newline_after_pre_listing_or_textarea_is_dropped(
    page, tag, text
):
    """HTML drops a newline that comes right after a pre, listing or
    textarea start tag, so a word before a textarea joins its text."""
    assert parse_html(page).find(f".//{tag}").text == text


def test_invented_newline_after_another_token_is_kept():
    """Only a newline that is the very next token goes: after a comment, a
    start tag or an end tag, it is text. html5lib 1.1 keeps it in each case
    but one: after a start tag it ignores, such as a later html start tag,
    it drops the newline, though the start tag came first."""
    pre = parse_html("<pre><!-- w0 -->\nw1</pre>").find(".//pre")
    assert pre.text == "\nw1"
    assert parse_html("<pre><b>\nw0</b></pre>").find(".//b").text == "\nw0"
    assert parse_html("<pre><html>\nw0</pre>").find(".//pre").text == "\nw0"
    assert parse_html("<p><pre></pre>\nw0").find(".//pre").tail == "\nw0"


def test_invented_carriage_returns_read_as_newlines():
    root = parse_html("<pre>w0\r\nw1\rw2</pre><script>w3\r\nw4</script>")
    assert root.find(".//pre").text == "w0\nw1\nw2"
    assert root.find(".//script").text == "w3\nw4"


# The round-10 review's findings, invented pages only.


def invented_after_a_chart(fragment: str) -> bytes:
    """Nevada's section and its Individual chart, then ``fragment`` and a
    second chart."""
    return invented_nevada_with("") + (
        f"{fragment}<table>{INVENTED_HEADER}</table>".encode()
    )


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's Medium 1 table, each after a first chart.
        "<h4>Individual<br>or couple</h4>",
        "<h4>Individual<br>and couple</h4>",
        "<h4>Couple</h4><p>Individual<br>or couple</p>",
        "<h4>Couple<br>Eligible individual</h4>",
        "<h4>Couple<div>Invented note on each individual</div></h4>",
        # Its control, one line, refuses the same way.
        "<h4>Individual or couple</h4>",
        # A plural counts, in a claimant line's block as elsewhere.
        "<h4>Individual<br>Couples</h4>",
        # Round 11's R1 witness: the other type in a prose line of 80
        # characters or more, after the claimant line or before it, and in
        # a list item.
        "<p>Couple<br>Invented payments go to each eligible individual"
        f"{INVENTED_LONG_TAIL}</p>",
        "<p>Invented payments go to each eligible individual"
        f"{INVENTED_LONG_TAIL}<br>Couple</p>",
        "<ul><li>Individual<br>Invented note on each eligible couple"
        f"{INVENTED_LONG_TAIL}</li></ul>",
    ],
)
def test_invented_block_with_a_claimant_line_counts_every_view(fragment):
    """Regression (the round-10 review's Medium 1): the words of a block
    with a claimant line were counted only in its claimant lines, so a
    second type in prose across a ``br`` read as one type. Every view of
    such a block counts, its whole text and its long prose lines
    included."""
    with pytest.raises(TableStructureError, match="two claimants"):
        describe_poms_tables(invented_after_a_chart(fragment))


@pytest.mark.parametrize(
    ("first", "fragment", "expected"),
    [
        # The review's m1 repros: K1 to K26 after a first claimant heading,
        # then its captions C1 to C8. Each refuses or reads right.
        ("Couple", "<h5>Eligible individual</h5>", "lacks state or claimant"),
        ("Couple", "<h5>Individual living alone</h5>", "lacks state or"),
        ("Individual", "<h4>Couple (both eligible)</h4>", "lacks state or"),
        ("Couple", "<h4>Individual or couple for Nevada</h4>", "two claim"),
        ("Couple", "<p>Individual and couple</p>", "two claimants"),
        ("Individual", "<h4>Couple:</h4>", "lacks state or claimant"),
        ("Individual", "<h4>Couple payment levels:</h4>", "lacks state or"),
        ("Individual", "<h4>Couple Payment Level</h4>", "couple"),
        (
            "Individual",
            "<h4>Couple payment levels for Nevada:</h4>",
            "lacks state or claimant",
        ),
        ("Individual", "<h4>Couple - Nevada</h4>", "lacks state or claimant"),
        ("Individual", "<h4>Couples</h4>", "lacks state or claimant"),
        ("Individual", "<h4>Eligible couple</h4>", "lacks state or claimant"),
        ("Individual", "<h4>Couple (continued)</h4>", "lacks state or"),
        ("Individual", "<h4>Payment levels: couple</h4>", "lacks state or"),
        (
            "Individual",
            f"<table>{INVENTED_HEADER}</table><h4>Couple payment levels</h4>",
            "couple",
        ),
        ("Individual", "<h4>(b) Couple</h4>", "lacks state or claimant"),
        ("Individual", "<h4>b) Couple</h4>", "couple"),
        ("Individual", "<h4>B. COUPLE</h4>", "couple"),
        ("Individual", "<h4>Couple&nbsp;payment levels</h4>", "couple"),
        (
            "Individual",
            "<h4>Couple payment levels for the State of Nevada</h4>",
            "lacks state or claimant",
        ),
        (
            "Individual",
            "<h4>Couple payment levels in Nevada</h4>",
            "lacks state or claimant",
        ),
        (
            "Individual",
            "<h4>Couple payment levels for NV</h4>",
            "lacks state or claimant",
        ),
        (
            "Individual",
            "<h4>Couple payment levels for Nev.</h4>",
            "lacks state or claimant",
        ),
        ("Individual", "<h4>Recipient couple</h4>", "two claimants"),
        ("Individual", "<h4>Couple recipient</h4>", "two claimants"),
        ("Couple", "<h4>Individual recipient</h4>", "lacks state or claim"),
        (
            "Individual",
            "<p>Couple payment levels effective January 1, 2030 Couple</p>",
            "couple",
        ),
        (
            "Individual",
            "<p>Nevada Effective January 1, 2030 for Utah Couple</p>",
            "section heading",
        ),
        (
            "Individual",
            "<p>Effective January 1, 2031 Utah Couple</p>",
            "section heading",
        ),
        (
            "Couple",
            "<p>Payment levels effective for invented cases until January 1,"
            " 2030 Individual</p>",
            "individual",
        ),
        ("Couple", "<p>Nevada Effective 1/1/30 Individual</p>", "individual"),
        (
            "Couple",
            "<p>Effective January 1, 2030, individual</p>",
            "lacks state or claimant",
        ),
        (
            "Couple",
            "<p>Effective January 1, 2030: Individual</p>",
            "lacks state or claimant",
        ),
        (
            "Couple",
            "<p>Effective January 1, 2030 - Individual</p>",
            "lacks state or claimant",
        ),
        # The review's realistic shape.
        (
            "Individual",
            "<p>No supplement.</p><h4>Couple payment levels for Nevada:</h4>",
            "lacks state or claimant",
        ),
    ],
)
def test_invented_unread_claimant_heading_leaves_no_earlier_claimant(
    first, fragment, expected
):
    """Regression (the round-10 review's Medium 2): a heading or short line
    that the claimant pattern does not admit left the claimant line before
    it standing, so the chart read that earlier type silently. Such a line
    now names a claimant the reader does not read, and the chart refuses
    unless a later claimant line names one; a line that holds both types
    refuses as naming two, as K4 does."""
    payload = invented_nevada_after(first, fragment)
    if expected in {"individual", "couple"}:
        *_, last = describe_poms_tables(payload)
        assert (last["state"], last["claimant_type"]) == ("Nevada", expected)
    else:
        with pytest.raises(TableStructureError, match=expected):
            describe_poms_tables(payload)


UNREAD_CLAIMANT_FORMS = [
    "{w}:",
    "{w}s",
    "Eligible {w}",
    "{w} (continued)",
    "{w} payment levels:",
    "Payment levels: {w}",
    "(b) {w}",
    "{w} payment levels in Nevada",
    "{w} - Nevada",
    "{w} payment levels for the State of Nevada",
    "Invented eligibility rules: {w}",
    "Effective January 1, 2030, {w}",
]


@settings(deadline=None, max_examples=200)
@given(
    st.sampled_from(["Individual", "Couple"]),
    st.sampled_from(["h4", "h5", "p", "div", "blockquote"]),
    st.sampled_from(UNREAD_CLAIMANT_FORMS + ["{w}", "{w} payment levels"]),
    st.sampled_from([str, str.lower, str.upper]),
)
def test_invented_later_claimant_line_never_charts_the_earlier_type(
    first, tag, form, case
):
    """Property: after a claimant heading, a heading or short line that
    names the other claimant type, in a form the claimant pattern admits
    or not, never charts the first type: the chart reads the other type or
    refuses."""
    other = "Couple" if first == "Individual" else "Individual"
    line = case(form.format(w=other))
    payload = invented_nevada_after(first, f"<{tag}>{line}</{tag}>")
    try:
        *_, last = describe_poms_tables(payload)
    except TableStructureError:
        return
    assert last["claimant_type"] == other.lower()


@pytest.mark.parametrize(
    "line",
    [
        # The review's E9 and E10, and more forms that name another State
        # past a short line's start.
        "Supplements for Utah",
        "Optional supplement: Utah",
        "Invented note on Utah",
        "Payment levels in UT",
        "Notes on N.J. cases",
        "Residents who move from California",
    ],
)
def test_invented_short_line_naming_another_state_is_refused(line):
    """Regression (round 11's carry-over sweep): a short line that named
    another State past its start, as a section may open, charted the
    section before it on. Any line under 80 characters that names another
    State now refuses."""
    with pytest.raises(TableStructureError, match="short line names another"):
        describe_poms_tables(
            invented_nevada_with(f"<p>{line}</p><p>Couple</p>")
        )


@pytest.mark.parametrize(
    "block",
    [
        # Round 11's R9 witness: the short line follows a long one.
        "<p>" + "Invented filler " * 6 + "<br>Supplements for Utah</p>",
        # The short line before a long one, and in a list item.
        f"<p>Invented note on Utah<br>Invented note{INVENTED_LONG_TAIL}</p>",
        f"<ul><li>Invented note{INVENTED_LONG_TAIL}<br>Payment levels in UT"
        "</li></ul>",
    ],
)
def test_invented_short_line_of_a_long_block_naming_another_state_is_refused(
    block,
):
    """The short-line State net reads every line of a block, not only its
    whole text, so a short line that names another State refuses even when
    the block's whole text runs past 80 characters. Round 11's mutant R9,
    which read the whole text only, charted these under Nevada."""
    with pytest.raises(TableStructureError, match="short line names another"):
        describe_poms_tables(invented_nevada_with(block + "<p>Couple</p>"))


@settings(deadline=None, max_examples=150)
@given(
    st.sampled_from(GLUED_NAMES),
    st.sampled_from(
        [
            "Supplements for {}",
            "Invented note on {}",
            "Payment levels in {}",
            "Optional supplement: {}",
            "Residents who move from {} here",
            "{} (continued)",
            "The State of {}",
        ]
    ),
    st.sampled_from(INVENTED_BLOCK_KINDS),
)
def test_invented_short_line_naming_another_state_never_charts_nevada(
    named, form, kind
):
    """Property: a line under 80 characters, in a block of any kind, that
    names another State anywhere never charts under Nevada's selector."""
    text, _ = named
    line = invented_block("p", form.format(text), kind, False)
    assert invented_nevada_outcome(line + "<p>Couple</p>") is None


def test_invented_long_line_naming_another_state_is_prose():
    """A Limit: a line of 80 characters or more that names another State in
    other words is prose, and the section reads on."""
    payload = invented_nevada_with(
        f"<p>Supplements for Utah{INVENTED_LONG_TAIL}</p><p>Couple</p>"
    )
    assert invented_selector(payload)[:2] == ("Nevada", "couple")


@pytest.mark.parametrize(
    "fragment",
    [
        # Round 11's carry-over sweep: a heading or short line that names a
        # date in a form no effective-date sentence takes.
        "<p>Payment levels as of January 1, 2031</p>",
        "<p>Effective: January 1, 2031</p>",
        "<h5>January 1, 2031</h5>",
        "<p>Eff. 1/1/2031</p>",
        "<p>Beginning March 1, 2031</p>",
        "<h5>Payment levels beginning 3/1/31</h5>",
        "<p>Revised March 1, 2031</p>",
        "<div>Invented note<br>Payments as of 4/1/2031</div>",
        # The date split across a line break, which only the whole text
        # dates.
        "<p>Payment levels as of January 1,<br>2031</p>",
        # Dates in forms no sentence reads, in a sentence or not.
        "<p>Payment levels as of Jan. 1, 2031</p>",
        "<p>Payment levels effective January 2031</p>",
        "<p>Effective 1 March 2031</p>",
        "<h5>Payment levels 2031-03-01</h5>",
        "<p>Revised 3-1-2031</p>",
        # Round 11's R17 witness: a heading of 80 characters or more.
        f"<h5>Payment levels as of January 1, 2031{INVENTED_LONG_TAIL}</h5>",
        # Its R18 witness: a date that only the unmarked reading shows, as a
        # link to a footnote on another page splits it, and one that only
        # the bare reading shows.
        "<p>Payment levels as of Jan<a href='0501415010#fn1'>1</a>uary 1,"
        " 2031</p>",
        "<p>Payment levels as of Jan<sup>1</sup>uary 1, 2031</p>",
    ],
)
def test_invented_unread_date_line_makes_the_next_chart_refuse(fragment):
    """Regression (round 11's carry-over sweep): a later line that named a
    new date in a form the reader does not read left the section's earlier
    date standing, so the chart carried it silently. Such a line now
    leaves the date unread, and the next chart refuses. A heading names a
    date whatever its length, and a line names one in its joined, bare or
    unmarked reading."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_unread_date_stands_until_a_sentence_dates_the_section():
    """An unread date line refuses every later chart of the section until
    an effective-date sentence dates it again, and a State heading starts
    afresh."""
    unread = (
        invented_nevada_with("")
        + (
            "<p>Revised March 1, 2031</p><h4>Couple</h4>"
            f"<table>{INVENTED_HEADER}</table>"
        ).encode()
    )
    with pytest.raises(TableStructureError, match="table 2 follows a date"):
        describe_poms_tables(unread)
    redated = invented_nevada_with(
        "<p>Revised March 1, 2031</p>"
        "<p>Payment levels effective April 1, 2031</p>"
    )
    assert invented_selector(redated)[2] == "2031-04-01"
    # The round-11 review's X9: a State heading after the unread date starts
    # Utah's section afresh, with no date of its own.
    (afresh,) = describe_poms_tables(
        invented_payload(
            "<h3>Nevada</h3>"
            + invented_definitions([("A", "Invented Nevada definition")])
            + "<p>Monthly payment levels effective January 1, 2030</p>"
            "<p>Revised March 1, 2031</p><h3>Utah</h3><h4>Couple</h4>"
            f"<table>{INVENTED_HEADER}</table>"
        )
    )
    assert (
        afresh["state"],
        afresh["claimant_type"],
        afresh["effective_from"],
        afresh["date_options"],
    ) == ("Utah", "couple", None, {"not_stated": None})


@pytest.mark.parametrize(
    ("fragment", "date"),
    [
        # The section's own date, a footnote body that opens with its
        # marker, and the revision line date no chart.
        ("<p>Payment levels as of January 1, 2030</p>", "2030-01-01"),
        ("<p><sup>1</sup>Revised March 1, 2031</p>", "2030-01-01"),
        ("<p>Effective Dates: 02/03/2041 - Present</p>", "2030-01-01"),
        # A Limit: a line of 80 characters or more that dates in another
        # form is prose.
        (
            f"<p>Invented note dated March 1, 2031{INVENTED_LONG_TAIL}</p>",
            "2030-01-01",
        ),
        # A later sentence dates the chart.
        ("<p>Effective March 1, 2031</p>", "2031-03-01"),
    ],
)
def test_invented_other_date_lines_leave_the_date_read(fragment, date):
    assert invented_selector(invented_nevada_with(fragment))[2] == date


@settings(deadline=None, max_examples=200)
@given(
    st.dates(min_value=date(2031, 1, 1), max_value=date(2039, 12, 28)),
    st.sampled_from(["{long}", "{numeric}"]),
    st.sampled_from(
        [
            "Payment levels as of {}",
            "Effective: {}",
            "{}",
            "Revised {}",
            "Eff. {}",
            "Beginning {}",
            "Payment levels effective {}",
            "Effective {}",
            "Nevada Effective {}",
        ]
    ),
    st.sampled_from(["p", "h5", "div", "li"]),
)
def test_invented_later_date_line_never_charts_the_earlier_date(
    day, style, form, tag
):
    """Property: after the section's date sentence, a heading or short line
    that names another date, as a sentence or not, never charts the
    earlier date: the chart reads the new date or refuses."""
    text = style.format(
        long=f"{day:%B} {day.day}, {day.year}",
        numeric=f"{day.month}/{day.day}/{day.year}",
    )
    line = form.format(text)
    block = (
        f"<ul><li>{line}</li></ul>"
        if tag == "li"
        else f"<{tag}>{line}</{tag}>"
    )
    try:
        selector = invented_selector(invented_nevada_with(block))
    except TableStructureError:
        return
    assert selector[2] == day.isoformat()


@pytest.mark.parametrize(
    "date",
    [
        # The review's Low 1 (D1, D2): a marker whose script or style the
        # bare reading dropped joined the day.
        "January 1<sup>5<script>x</script></sup>, 2031",
        "January 1<sup>5<style>x</style></sup>, 2031",
        # Its Note 1 (D3 to D5): links by the table cells' rule.
        "January 1<a href='https://www.ssa.gov/invented/0501415010#fn5'>5</a>,"
        " 2031",
        "January 1<a href='0501415010#fn5'>5</a>, 2031",
        "January 1<a href=' #fn5'>5</a>, 2031",
        # A longer sup, and an ordinal (Note 6).
        "January 1<sup>1234</sup>, 2031",
        "January 1<sup>st</sup>, 2031",
    ],
)
def test_invented_marker_by_either_rule_inside_a_date_is_refused(date):
    """Regression: a marker holding a script joined a date, and a link to a
    footnote by a full or relative URL changed one, silently. A date
    sentence must read the same without any element either marker rule
    counts."""
    payload = invented_nevada_with("").replace(
        b"effective January 1, 2030", f"effective {date}".encode(), 1
    )
    with pytest.raises(TableStructureError, match="reads differently"):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    "date", ["Janu<span>ary</span> 1, 2031", "January <b>1</b>, 2031"]
)
def test_invented_inline_element_inside_a_date_reads_joined(date):
    """A date sentence is read joined, as HTML renders inline elements, and
    only its bare and unmarked readings must date it the same, so an inline
    element inside its date, which the spaced reading splits, dates the
    chart. Round 11's mutant R36 (the round-10 review's M22, ported)
    compared the spaced reading instead and refused these."""
    payload = invented_nevada_with("").replace(
        b"effective January 1, 2030", f"effective {date}".encode(), 1
    )
    assert invented_selector(payload) == (
        "Nevada",
        "individual",
        "2031-01-01",
        [0],
    )


def test_invented_marker_text_drops_script_and_style():
    """A marker's text holds no script or style text, as no reading does,
    so the bare reading drops ``<sup>1<script>x</script></sup>``."""
    for inner in ("<script>x</script>", "<style>x</style>"):
        element = next(
            iter(parse_html(f"<p>Utah<sup>1{inner}</sup></p>").iter("p"))
        )
        ((joined, bare, _),) = _line_renderings(element)
        assert (joined, bare) == ("Utah1", "Utah")


@pytest.mark.parametrize(
    "caption",
    [
        # The review's Low 2 forms: list labels and leading punctuation.
        "<p>1. Utah (continued)</p>",
        "<p>2) Utah</p>",
        "<p>(b) Utah</p>",
        "<p>b) Utah</p>",
        "<p>- Utah</p>",
        "<p>&bull; Utah</p>",
        "<p>&ldquo;Utah&rdquo; (continued)</p>",
        "<p>(Utah)</p>",
        "<p>The State of Utah</p>",
        # The review's M21 witness: only the bare reading opens with Utah.
        "<p><sup>1</sup>Utah (continued)</p>",
    ],
)
def test_invented_caption_net_takes_labels_and_punctuation(caption):
    """Regression (the round-10 review's Low 2): the caption net took only
    an "A." label, so these captions of another State read under Nevada's
    selector."""
    with pytest.raises(TableStructureError, match="another State's caption"):
        describe_poms_tables(invented_nevada_with(caption + "<p>Couple</p>"))


@pytest.mark.parametrize(
    "script",
    [
        # The review's Low 3 (S1) and a legacy document.write form (S2).
        "<script><!--<script></script><h3>Utah</h3><h4>Couple</h4>-->"
        "</script>",
        "<script type='text/javascript'><!--\ndocument.write(\"<script"
        " src='x.js'></script>\");\n</script><h3>Utah</h3><h4>Couple</h4>"
        "//--></script>",
        "<SCRIPT><!-- <SCRIPT/></script>",
    ],
)
def test_invented_script_with_an_escaped_script_refuses_the_page(script):
    """Regression (the round-10 review's Low 3): after "<!--" and a script
    start tag, HTML runs a script on past its next end tag, which neither
    Python does, so the tree read text as markup."""
    with pytest.raises(TableStructureError, match="escaped script"):
        describe_poms_tables(invented_nevada_with(script))


@pytest.mark.parametrize(
    "script",
    [
        "<script><!-- invented() --></script>",
        "<script><!--<scriptx></script>",
        "<script>var w0 = '<script>';</script>",
        # The round-11 review's X10 and X11: "<!-" is no escape start, and
        # a script start tag before "<!--" is none after it.
        "<script><!-<script></script>",
        "<script><script>w0<!--</script>",
    ],
)
def test_invented_other_scripts_are_read_as_before(script):
    root = parse_html(f"<p>w0{script}w1</p>")
    assert normalized_text(root.find(".//p")).endswith("w1")


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        # The review's M4 witness: only the bare reading is a dated
        # sentence, and its joined reading holds no date.
        (
            "<p>Eff<sup>1</sup>ective January 1<sup>2</sup>, 20<sup>3</sup>31"
            "</p>",
            "reads only without its footnote markers",
        ),
        # M20's witness: a caption whose State date line holds "Effective
        # Dates:" names its claimant; a date there that no sentence states
        # leaves the chart's date unread.
        (
            "<p>Nevada Effective Dates: 1/1/2031 Couple</p>",
            "no effective-date sentence states",
        ),
    ],
)
def test_invented_round_10_mutant_witnesses_are_refused(fragment, message):
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        # M20's: "Effective Dates:" keeps a State date line from being an
        # effective-date line, but the caption still names its claimant.
        (
            "<p>Nevada Effective Dates: for Nevada Couple</p>",
            ("Nevada", "couple", "2030-01-01", [0]),
        ),
    ],
)
def test_invented_round_10_mutant_witnesses_read(fragment, expected):
    assert invented_selector(invented_nevada_with(fragment)) == expected


def test_invented_repeated_date_is_one_date():
    """The review's M16 witness: a sentence that states one date twice
    dates the chart, with no alternatives."""
    payload = invented_nevada_with("").replace(
        b"effective January 1, 2030",
        b"effective January 1, 2031 (January 1, 2031)",
        1,
    )
    (context,) = describe_poms_tables(payload)
    assert (context["effective_from"], context["date_options"]) == (
        "2031-01-01",
        {},
    )


@pytest.mark.parametrize(
    ("block", "dates"),
    [
        # The review's Note 2 (D29): a block of 400 characters or more with
        # two date sentences that differ.
        (
            "<p>Monthly payment levels effective January 1, 2031<br>"
            + "Invented filler " * 30
            + "<br>Payment levels effective February 1, 2031</p>",
            ("2031-01-01", "2031-02-01"),
        ),
        # Two ranges in one sentence, and a range beside another date.
        (
            "<p>Payment levels effective from March 1, 2031 to June 30, 2031"
            " and from July 1, 2031 to December 31, 2031</p>",
            ("2031-03-01", "2031-06-30", "2031-07-01", "2031-12-31"),
        ),
        (
            "<p>Payment levels effective from March 1, 2031 to June 30, 2031"
            + INVENTED_FILLER
            + "Payment levels effective July 1, 2031</p>",
            ("2031-03-01", "2031-06-30", "2031-07-01"),
        ),
        # Round 11's R32 witness: a range and a sentence that starts on the
        # same day, two dates in all, still date differently.
        (
            "<p>Payment levels effective from March 1, 2031 to June 30, 2031"
            + INVENTED_FILLER
            + "Payment levels effective March 1, 2031</p>",
            ("2031-03-01", "2031-06-30"),
        ),
    ],
)
def test_invented_conflicting_dates_remain_named_alternatives(block, dates):
    """Regression (the round-10 review's Note 2): a long block took its
    first date sentence silently, and a range with other than two dates
    named none. Their dates now remain named alternatives, with no chosen
    date."""
    (context,) = describe_poms_tables(invented_nevada_with(block))
    assert context["effective_from"] is None
    assert context["effective_to"] is None
    assert context["date_options"] == {
        f"source_date_{i + 1}": value for i, value in enumerate(dates)
    }


def test_invented_long_block_whose_sentences_agree_dates_the_chart():
    block = (
        "<p>Monthly payment levels effective January 1, 2031"
        + INVENTED_FILLER
        + "Payment levels for each invented case effective January 1, 2031"
        "</p>"
    )
    (context,) = describe_poms_tables(invented_nevada_with(block))
    assert context["effective_from"] == "2031-01-01"
    assert context["parameter_effective_date_text"] == (
        "Monthly payment levels effective January 1, 2031"
    )


def test_invented_range_split_across_a_line_break_dates_from_and_to():
    """A block's whole text is its date sentence when it is one, so a range
    split across a ``br`` dates the chart from and to, though its first
    line alone is a sentence with one date. Round 11's mutant R34, which
    read the lines only, named the two dates as alternatives."""
    block = (
        "<p>Payment levels effective from March 1, 2031<br>"
        "to June 30, 2031</p>"
    )
    (context,) = describe_poms_tables(invented_nevada_with(block))
    assert (
        context["effective_from"],
        context["effective_to"],
        context["date_options"],
        context["parameter_effective_date_text"],
    ) == (
        "2031-03-01",
        "2031-06-30",
        {},
        "Payment levels effective from March 1, 2031 to June 30, 2031",
    )


# Round 12 answers the round-11 review.


def invented_padded(opening: str, length: int) -> str:
    """``opening`` and invented filler, cut to exactly ``length``
    characters; the filler names no State, claimant word, date or year."""
    line = (opening + " " + "x" * length)[:length]
    assert len(line) == length and not line.endswith(" ")
    return line


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's controls P0 and L10, which refused already.
        "<p>Payment levels as of March 1, 2031</p>",
        "<p>See also Effective March 1, 2031</p>",
        # Its Low 1 leaks: a footnote body's line exempted another line of
        # its block that named the same date (P1); a revision range
        # exempted the line or block that held it (P2, P2b, P2c); and a
        # leading longer sup or link to a footnote, or one wrapping the
        # whole line, made a footnote body (L8, L9, M14, P3e).
        "<p>Payment levels as of March 1, 2031<br><sup>1</sup>Revised"
        " March 1, 2031</p>",
        "<p>Effective Dates: 01/01/2030 - Present<br>Payment levels as of"
        " March 1, 2031</p>",
        "<p>Payment levels as of March 1, 2031 (Effective Dates: 03/01/2031"
        " - Present)</p>",
        "<h5>Payment levels effective March 1, 2031 (Effective Dates:"
        " 03/01/2031 - Present)</h5>",
        "<p><a href='#fn3'>See also</a> Effective March 1, 2031</p>",
        "<p><sup>Invented note:</sup> Effective March 1, 2031</p>",
        "<h5><a href='#fn1'>Payment levels as of March 1, 2031</a></h5>",
        "<h5><a href='#fn2'>Payment levels as of</a> March 1, 2031</h5>",
    ],
    ids=["P0", "L10", "P1", "P2", "P2b", "P2c", "L8", "L9", "M14", "P3e"],
)
def test_invented_footnote_or_revision_text_exempts_no_other_date(fragment):
    """Regression (the round-11 review's Low 1): the unread-date net
    exempted every date that a footnote body or revision line named, across
    its whole block, and took any leading sup or link to a footnote for a
    marker, so these lines kept the section's 2030 date silently. Each line
    now names its own dates, without the revision range's text, and only
    markers of a marker's size make a footnote body."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    ("fragment", "between", "expected"),
    [
        # The review's "keep their current outcomes" cases: R15's witness
        # and a footnote body between two charts, the revision line, and
        # X7's witness, whose whole text names only the footnote's date.
        (
            "<p><a href='0501415010#fn1'>1</a>Revised March 1, 2031</p>"
            "<h4>Couple</h4>",
            True,
            ("Nevada", "couple", "2030-01-01"),
        ),
        (
            "<p><sup>1</sup>Revised March 1, 2031</p><h4>Couple</h4>",
            True,
            ("Nevada", "couple", "2030-01-01"),
        ),
        (
            "<p>Effective Dates: 02/03/2041 - Present</p>",
            False,
            ("Nevada", "individual", "2030-01-01"),
        ),
        (
            "<div>Invented note<br><sup>1</sup>Revised March 1, 2031</div>",
            False,
            ("Nevada", "individual", "2030-01-01"),
        ),
        # And the date split across a br, which still refuses.
        ("<p>Payment levels as of January 1,<br>2031</p>", False, None),
    ],
    ids=["R15", "footnote-body", "revision", "X7", "split"],
)
def test_invented_footnote_bodies_and_revision_lines_keep_their_outcomes(
    fragment, between, expected
):
    payload = (
        invented_after_a_chart(fragment)
        if between
        else invented_nevada_with(fragment)
    )
    if expected is None:
        with pytest.raises(TableStructureError, match="no effective-date"):
            describe_poms_tables(payload)
        return
    *_, last = describe_poms_tables(payload)
    assert (
        last["state"],
        last["claimant_type"],
        last["effective_from"],
    ) == expected


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's N9 to N11, and svg's title, a textarea and an xmp.
        "<svg><script><h3>Utah</h3><h4>Couple</h4></script></svg>",
        "<svg><style><h3>Utah</h3><h4>Couple</h4></style></svg>",
        "<math><style><h3>Utah</h3><h4>Couple</h4></style></math>",
        "<svg><title><h3>Utah</h3><h4>Couple</h4></title></svg>",
        "<svg><textarea><h3>Utah</h3></textarea></svg>",
        "<svg><g><xmp><h3>Utah</h3></xmp></g></svg>",
        # Over-refusals the tree's docstring names: HTML reads these as
        # text too.
        "<svg><style>w0 < w1</style></svg>",
        "<svg><foreignObject><script><h3>Utah</h3></script></foreignObject>"
        "</svg>",
    ],
)
def test_invented_raw_text_inside_svg_or_math_refuses_the_page(fragment):
    """Regression (the round-11 review's Low 2): HTML reads markup inside
    svg or math, so the h3 and h4 of N9 to N11 head Utah's couple chart
    there, while the tree held them as raw text and charted Nevada's
    individual one."""
    with pytest.raises(TableStructureError, match="inside svg or math"):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    "fragment",
    [
        # An icon as the pinned pages' svg elements are, and foreign
        # content whose raw text holds no "<".
        "<p>w0<svg><path d='M0 0'/><title>Invented icon</title></svg>w1</p>",
        "<svg><style>w0</style></svg>",
        "<math><mi>w0</mi></math>",
    ],
)
def test_invented_svg_or_math_without_markup_in_raw_text_is_read(fragment):
    assert invented_selector(invented_nevada_with(fragment)) == (
        "Nevada",
        "individual",
        "2030-01-01",
        [0],
    )


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's N7 and N8, and each other raw text or RCDATA element.
        "<script/><h3>Utah</h3><h4>Couple</h4></script>",
        "<script /><h3>Utah</h3><h4>Couple</h4></script>",
        "<SCRIPT/><h3>Utah</h3><h4>Couple</h4></SCRIPT>",
        "<style/><h3>Utah</h3><h4>Couple</h4></style>",
        "<xmp/><h3>Utah</h3><h4>Couple</h4></xmp>",
        "<iframe/><h3>Utah</h3><h4>Couple</h4></iframe>",
        "<noembed/><h3>Utah</h3><h4>Couple</h4></noembed>",
        "<noframes/><h3>Utah</h3><h4>Couple</h4></noframes>",
        "<textarea/><h3>Utah</h3><h4>Couple</h4></textarea>",
        "<title/><h3>Utah</h3><h4>Couple</h4></title>",
        # An over-refusal the tree's docstring names: HTML honours the
        # slash inside svg.
        "<svg><title/></svg>",
    ],
)
def test_invented_self_closed_raw_text_tag_refuses_the_page(fragment):
    """Regression (the round-11 review's Note 2): HTML ignores the slash of
    ``<script/>`` and holds what follows as the script's text, up to its
    end tag, while both Pythons read the headings after it as markup, so
    the chart read as Utah's couple."""
    with pytest.raises(TableStructureError, match="self-closed raw text"):
        describe_poms_tables(invented_nevada_with(fragment))


def invented_dated(date: str) -> bytes:
    """Nevada's section, its date sentence reading "effective ``date``"."""
    return invented_nevada_with("").replace(
        b"effective January 1, 2030", f"effective {date}".encode(), 1
    )


@pytest.mark.parametrize(
    ("date", "dates"),
    [
        # The review's G1 and G2: a "to" that no date follows.
        (
            "from January 1, 2031 apply to facilities licensed after July 1,"
            " 2030",
            ("2031-01-01", "2030-07-01"),
        ),
        (
            "from March 1, 2031 to residents of homes licensed before June 30,"
            " 2031",
            ("2031-03-01", "2031-06-30"),
        ),
        # A "from" that no date follows.
        (
            "from the first day of the month after March 1, 2031 to June 30,"
            " 2031",
            ("2031-03-01", "2031-06-30"),
        ),
    ],
    ids=["G1", "G2", "from"],
)
def test_invented_prose_to_or_from_ends_no_range(date, dates):
    """Regression (the round-11 review's Low 3): any "to" after "effective
    from" ended a range, so G1 dated the chart from 2031 to 2030 and G2 to
    June 30, 2031, silently. A range now needs a date right after "from"
    and right after "to" or "through", so these name their dates as
    alternatives."""
    (context,) = describe_poms_tables(invented_dated(date))
    assert (context["effective_from"], context["effective_to"]) == (None, None)
    assert context["date_options"] == {
        f"source_date_{i + 1}": value for i, value in enumerate(dates)
    }


@pytest.mark.parametrize(
    "date",
    [
        # The review's G4 and Note 5's G6, and a numeric "through" range.
        "from June 30, 2031 to March 1, 2031",
        "from March 1, 2031 to March 1, 2031",
        "from 6/30/2031 through 3/1/2031",
    ],
)
def test_invented_range_that_does_not_end_after_it_starts_refuses(date):
    """Regression (the round-11 review's Low 3 and Note 5): a reversed range
    dated the chart from its later date to its earlier one, and a range from
    a date to the same date dropped its end, silently. Both now refuse; a
    range meant as one day refuses too, an over-refusal the Limits list
    names."""
    with pytest.raises(TableStructureError, match="does not end after it"):
        describe_poms_tables(invented_dated(date))


@pytest.mark.parametrize(
    "date",
    [
        "from March 1, 2031 to June 30, 2031",
        "from March 1, 2031, to June 30, 2031",
        # The review's G5: "through" ends a range as "to" does.
        "from March 1, 2031 through June 30, 2031",
        "from 3/1/2031 to 6/30/2031",
    ],
)
def test_invented_range_dates_the_chart_from_and_to(date):
    (context,) = describe_poms_tables(invented_dated(date))
    assert (
        context["effective_from"],
        context["effective_to"],
        context["date_options"],
    ) == ("2031-03-01", "2031-06-30", {})


def test_invented_range_dates_the_chart_in_its_own_order():
    """A sentence that names its range's end first, and no other date,
    dates the chart from the range's start to its end; 858fb546 read its
    dates in the order the sentence names them, from June 30 to March 1."""
    (context,) = describe_poms_tables(
        invented_nevada_with(
            "<p>Payment levels effective June 30, 2031: effective from March"
            " 1, 2031 to June 30, 2031</p>"
        )
    )
    assert (context["effective_from"], context["effective_to"]) == (
        "2031-03-01",
        "2031-06-30",
    )


@settings(deadline=None, max_examples=150)
@given(
    st.dates(min_value=date(2031, 1, 1), max_value=date(2039, 12, 28)),
    st.dates(min_value=date(2031, 1, 1), max_value=date(2039, 12, 28)),
    st.sampled_from(["to", "through"]),
    st.booleans(),
)
def test_invented_range_never_ends_before_it_starts(start, end, word, numeric):
    """Property: a range dates the chart from its start to its end when it
    ends after it starts, and refuses otherwise, whatever its dates, its
    word and its date form."""

    def written(day):
        if numeric:
            return f"{day.month}/{day.day}/{day.year}"
        return f"{day:%B} {day.day}, {day.year}"

    payload = invented_dated(f"from {written(start)} {word} {written(end)}")
    if end <= start:
        with pytest.raises(TableStructureError, match="does not end after"):
            describe_poms_tables(payload)
        return
    (context,) = describe_poms_tables(payload)
    assert (
        context["effective_from"],
        context["effective_to"],
        context["date_options"],
    ) == (start.isoformat(), end.isoformat(), {})


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's F1 to F6 and F8: a later year in a form no sentence
        # reads, in a heading.
        "<h5>Payment levels as of January 1st, 2031</h5>",
        "<h5>Payment levels as of January 1,2031</h5>",
        "<h5>Payment levels for 2031</h5>",
        "<h5>Payment levels as of 1/2031</h5>",
        "<h5>Payment levels as of 01.01.2031</h5>",
        "<h5>Payment levels as of 2031/01/01</h5>",
        "<h5>Calendar year 2031 payment levels</h5>",
        # In a short line, and a year glued to letters.
        "<p>Payment levels for 2031</p>",
        "<div>Calendar year 2031 payment levels</div>",
        "<ul><li>FY2031 levels</li></ul>",
        # A heading that holds an earlier year.
        "<h5>Payment levels for 2029</h5>",
        # Over-refusals the Limits list names: a later year that concerns
        # something else, and a sentence whose date no sentence reads.
        "<p>Revised 2031</p>",
        "<p>Section 2031 rules</p>",
        "<p>Payment levels effective January 1st, 2031</p>",
    ],
)
def test_invented_year_outside_the_dates_in_force_leaves_the_date_unread(
    fragment,
):
    """Regression (the round-11 review's Low 4): a later year in a date form
    the net did not read, as "January 1st, 2031" or "Payment levels for
    2031", left the section's 2030 date standing silently. A heading that
    holds a year outside the years of the dates in force, and a line under
    80 characters that holds a later one, now leave the date unread."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_any_year_counts_with_no_date_in_force():
    """With no date in force, as after a sentence that states none, a short
    line's year of any value leaves the date unread; without one, the chart
    names no date."""
    undated = invented_dated("as the invented note says")
    (context,) = describe_poms_tables(undated)
    assert context["date_options"] == {"not_stated": None}
    noted = undated.replace(
        b"<h4>Individual</h4>", b"<p>Notes for 2029</p><h4>Individual</h4>"
    )
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(noted)


@pytest.mark.parametrize(
    "fragment",
    [
        # A year in force, a long line, numbers that are no year, and the
        # revision range alone.
        "<p>Payment levels for 2030</p>",
        f"<p>Payment levels for 2031{INVENTED_LONG_TAIL}</p>",
        "<p>Section 1611 of the Act</p>",
        "<h5>Section 1611 of the Act</h5>",
        "<p>Section 2301 of the Act</p>",
        "<p>Invented code 120310</p>",
        "<p>Effective Dates: 02/03/2041 - Present</p>",
        "<p><sup>1</sup>Revised 2031</p>",
        # Limits the docstring names: an earlier year with no dating word in
        # a short line outside a heading, as one pinned page holds before a
        # chart; a two-digit year (the review's F11); and a year split
        # across a br.
        "<p>State-administered programs: For Calendar Year 2029 -</p>",
        "<h5>Payment levels as of January 1, 31</h5>",
        "<p>Payment levels for 20<br>31</p>",
    ],
)
def test_invented_other_years_leave_the_date_read(fragment):
    assert invented_selector(invented_nevada_with(fragment))[2] == (
        "2030-01-01"
    )


@settings(deadline=None, max_examples=150)
@given(
    st.integers(min_value=2031, max_value=2099),
    st.sampled_from(
        [
            "Payment levels as of January 1st, {}",
            "Payment levels as of January 1,{}",
            "Payment levels for {}",
            "Payment levels as of 1/{}",
            "Payment levels as of 01.01.{}",
            "Payment levels as of {}/01/01",
            "Calendar year {} payment levels",
            "FY{} levels",
            "Payment levels as of the first of January {}",
        ]
    ),
    st.sampled_from(["p", "h5", "div", "li"]),
)
def test_invented_later_year_line_never_charts_the_earlier_date(
    year, form, tag
):
    """Property: after the section's 2030 date sentence, a heading or short
    line that holds a later year in any of these forms makes the next chart
    refuse."""
    line = form.format(year)
    block = (
        f"<ul><li>{line}</li></ul>"
        if tag == "li"
        else f"<{tag}>{line}</{tag}>"
    )
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with(block))


@pytest.mark.parametrize(
    "date",
    [
        # The review's L1 and L3: links to a footnote whose href holds no
        # "fn".
        "January 1<a href='0501415010#note5'>5</a>, 2031",
        "January 1<a href='https://www.ssa.gov/invented/0501415010#n5'>5</a>,"
        " 2031",
        # A link of a marker's size that is no footnote marker, an
        # over-refusal the Limits list names.
        "January <a href='x.html'>1</a>, 2031",
    ],
)
def test_invented_link_of_marker_size_inside_a_date_is_refused(date):
    """Regression (the round-11 review's Low 5, item 3): a link to a
    footnote whose href held no "fn" joined the day, so these dated the
    chart January 15. A link whose text has a marker's size now refuses
    inside a date, whatever its href holds."""
    with pytest.raises(TableStructureError, match="reads differently"):
        describe_poms_tables(invented_dated(date))


def test_invented_line_dated_only_without_a_short_link_is_refused():
    with pytest.raises(TableStructureError, match="reads only without"):
        describe_poms_tables(
            invented_nevada_with(
                "<p>Payment<a href='x.html'>XX</a> levels effective January"
                " 1, 2031</p>"
            )
        )


def test_invented_short_link_outside_the_date_leaves_it_read():
    payload = invented_dated(
        "January 1, 2031 (see <a href='x.html'>SI</a> 01415.010)"
    )
    assert invented_selector(payload)[2] == "2031-01-01"


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        # X5: only the bare reading names Utah.
        (
            "<p>Supplements for Utah<sup>1</sup></p><p>Couple</p>",
            "short line names another State",
        ),
        # X15: only the whole text names New Jersey.
        (
            "<p>Supplements for New<br>Jersey</p><p>Couple</p>",
            "short line names another State",
        ),
        # X8: a date the reader cannot parse, in the year in force.
        (
            "<h5>Payment levels as of February 30, 2030</h5>",
            "no effective-date sentence states",
        ),
        # The 79-character side of the bounds X2, X3 and X4 moved, and of
        # the whole text's bound for a date split across a br.
        (
            f"<p>{invented_padded('Couple notes', 79)}</p>",
            "lacks state or claimant",
        ),
        (
            f"<p>{invented_padded('Supplements for Utah', 79)}</p>"
            "<p>Couple</p>",
            "short line names another State",
        ),
        (
            f"<p>{invented_padded('Payment levels as of March 1, 2031', 79)}"
            "</p>",
            "no effective-date sentence states",
        ),
        (
            f"<p>Payment levels as of 3/1/<br>{invented_padded('31', 53)}</p>",
            "no effective-date sentence states",
        ),
        # A leading pair of markers that join into a word longer than a
        # marker's, an over-refusal the Limits list names.
        (
            "<p><sup>12</sup><sup>34</sup>Revised March 1, 2031</p>",
            "no effective-date sentence states",
        ),
    ],
    ids=["X5", "X15", "X8", "X2-79", "X3-79", "X4-79", "whole-79", "pair"],
)
def test_invented_round_11_review_witnesses_are_refused(fragment, message):
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        # The 80-character side: a line of 80 characters, outside a
        # heading, is no short line to the claimant (X2), State (X3) and
        # date (X4) nets, and a whole text of 80 characters adds no date
        # split across its br.
        (
            f"<p>{invented_padded('Couple notes', 80)}</p>",
            ("Nevada", "individual", "2030-01-01", [0]),
        ),
        (
            f"<p>{invented_padded('Supplements for Utah', 80)}</p>"
            "<p>Couple</p>",
            ("Nevada", "couple", "2030-01-01", [0]),
        ),
        (
            f"<p>{invented_padded('Payment levels as of March 1, 2031', 80)}"
            "</p>",
            ("Nevada", "individual", "2030-01-01", [0]),
        ),
        (
            f"<p>{invented_padded('Payment levels for 2031', 80)}</p>",
            ("Nevada", "individual", "2030-01-01", [0]),
        ),
        (
            f"<p>Payment levels as of 3/1/<br>{invented_padded('31', 54)}</p>",
            ("Nevada", "individual", "2030-01-01", [0]),
        ),
        # Limits the docstring names: a claimant in other words (the
        # review's Note 4) leaves the Individual heading's claimant
        # standing, and a footnote body's later lines date no chart.
        (
            "<h4>Both members eligible</h4>",
            ("Nevada", "individual", "2030-01-01", [0]),
        ),
        (
            "<h4>Eligible spouses</h4>",
            ("Nevada", "individual", "2030-01-01", [0]),
        ),
        ("<h4>Married pair</h4>", ("Nevada", "individual", "2030-01-01", [0])),
        (
            "<p><sup>1</sup>Revised March 1, 2031<br>Payment levels as of"
            " March 1, 2031</p>",
            ("Nevada", "individual", "2030-01-01", [0]),
        ),
    ],
    ids=[
        "X2-80",
        "X3-80",
        "X4-80",
        "year-80",
        "whole-80",
        "both-members",
        "spouses",
        "pair",
        "footnote-block",
    ],
)
def test_invented_round_11_review_witnesses_read(fragment, expected):
    assert invented_selector(invented_nevada_with(fragment)) == expected


def test_invented_range_line_and_unranged_line_still_date_differently():
    """The review's X6 witness: a range line and a later sentence that names
    the same two dates without a range date differently, so the dates
    remain named alternatives; X6, which compared their dates alone, dated
    the chart from and to."""
    (context,) = describe_poms_tables(
        invented_nevada_with(
            "<p>Payment levels effective from March 1, 2031 to June 30, 2031"
            + INVENTED_FILLER
            + "Payment levels effective March 1, 2031 and June 30, 2031</p>"
        )
    )
    assert (context["effective_from"], context["effective_to"]) == (None, None)
    assert context["date_options"] == {
        "source_date_1": "2031-03-01",
        "source_date_2": "2031-06-30",
    }


@pytest.mark.parametrize(
    "fragment",
    [
        # A year that only the bare, unmarked or unlinked reading shows.
        "<p>Payment levels for 20<sup>1</sup>31</p>",
        "<p>Payment levels for 20<a href='x.html#fn1'>1</a>31</p>",
        "<p>Payment levels for 20<a href='x.html'>1</a>31</p>",
        # A date that only the unlinked reading shows, in the year in force.
        "<p>Payment levels as of Mar<a href='x.html'>1</a>ch 1, 2030</p>",
    ],
)
def test_invented_date_or_year_only_a_marker_free_reading_shows_is_unread(
    fragment,
):
    """The unread-date net reads a line's dates and years in its joined,
    bare, unmarked and unlinked readings, so a marker or short link that
    splits a year or date hides neither."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_date_inside_a_longer_link_is_read():
    """Only a link whose text has a marker's size leaves the unlinked
    reading, so a date sentence whose date a longer link holds dates the
    chart."""
    payload = invented_dated("<a href='x.html'>January 1, 2031</a>")
    assert invented_selector(payload)[2] == "2031-01-01"


# The round-12 review's findings, invented pages only.


def invented_nevada_2031_with(fragment: str) -> bytes:
    """``invented_nevada_with``, its section dated January 1, 2031."""
    return invented_nevada_with(fragment).replace(
        b"effective January 1, 2030", b"effective January 1, 2031", 1
    )


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's Low 1 table: dates in the section's own year, in
        # forms neither date pattern read.
        "<h5>Payment levels as of July 1st, 2030</h5>",
        "<p>Payment levels as of July 1st, 2030</p>",
        "<h5>Payment levels as of 07.01.2030</h5>",
        "<h5>Payment levels as of 2030/07/01</h5>",
        "<h5>Payment levels as of July 1,2030</h5>",
        "<p>Payment levels as of 7/2030</p>",
        "<h5>Payment levels as of<b>July</b> 1, 2030</h5>",
        "<h5>Payment levels as ofJuly 1, 2030</h5>",
        # The same alternatives in their other forms.
        "<p>Payment levels as of the 1st of July</p>",
        "<p>Payment levels as of 1st July 2030</p>",
        "<p>Payment levels as of July 1 st, 2030</p>",
        "<p>Payment levels as of July 1 , 2030</p>",
        "<p>Payment levels as of 2030.07.01</p>",
        "<p>Payment levels as of 07 / 2030</p>",
    ],
)
def test_invented_same_year_date_in_an_unread_form_leaves_the_date_unread(
    fragment,
):
    """Regression (the round-12 review's Low 1): the year net counts only
    years outside the dates in force, and neither date pattern read these
    forms, so a mid-year date in them kept the section's January date
    silently. Each form now names a date, and the next chart refuses."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_date_sentence_with_an_unread_second_date_is_refused():
    """The review's last Low 1 row: a short date sentence whose second date
    takes a form no sentence reads dropped that date."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(
            invented_dated("January 1, 2030 and July 1st, 2030")
        )


@pytest.mark.parametrize(
    ("date", "expected"),
    [
        # The forms the date patterns read still date the chart.
        ("July 1, 2030", "2030-07-01"),
        ("1/1/2030", "2030-01-01"),
        ("1 / 1 / 2030", "2030-01-01"),
        ("01/01/2030", "2030-01-01"),
    ],
)
def test_invented_date_sentence_in_a_read_form_still_dates_the_chart(
    date, expected
):
    assert invented_selector(invented_dated(date))[2] == expected


@pytest.mark.parametrize(
    "fragment",
    [
        # A year in force, a two-digit year a Limit leaves standing, and an
        # earlier year with no dating word.
        "<p>Payment levels for 2030</p>",
        "<p>Payment levels as of January 1, 31</p>",
        "<p>Invented note for 2029</p>",
        # A dating word only inside the revision range, which the net drops.
        "<p>Effective Dates: 02/03/2040 - Present (invented note for 2029)"
        "</p>",
    ],
)
def test_invented_line_without_an_unread_date_or_year_leaves_the_date_read(
    fragment,
):
    assert invented_selector(invented_nevada_with(fragment))[2] == (
        "2030-01-01"
    )


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's Note 2 cases: an earlier year in a short line that
        # speaks of payment levels.
        "<p>Payment levels for 2029</p>",
        "<p>Payment levels as of January 1st, 2029</p>",
        "<p>Payment levels as of 01.01.2029</p>",
        # Each dating word alone, one only the bare reading shows, and the
        # over-refusal the Limits list names ("Separate" holds "rate").
        "<p>Payment for 2029</p>",
        "<p>Benefit level for 2029</p>",
        "<p>Rules effective in 2029</p>",
        "<p>Notes as of 2029</p>",
        "<p>Rates for 2029</p>",
        "<p>Pay<sup>1</sup>ment for 2029</p>",
        "<p>Separate programs for 2029</p>",
    ],
)
def test_invented_earlier_year_with_a_dating_word_leaves_the_date_unread(
    fragment,
):
    """Regression (the round-12 review's Note 2): a short line outside a
    heading counted later years only, so "Payment levels for 2029" in a
    section dated 2030 kept its date silently. An earlier year now counts
    when the line holds a dating word."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's Low 2 table.
        "<p>Payment levels effective March 1, 2031<svg><section></section>"
        "</svg> and June 30, 2031</p>",
        "<p>Payment levels effective from March 1, 2031<svg><figure>"
        "</figure></svg> to June 30, 2031</p>",
        "<p>Payment levels<svg><article></article></svg> for Utah</p>"
        "<p>Individual</p>",
        "<svg><section>Couple</section></svg>",
        # Its "same happens with" forms.
        "<p>Payment levels effective March 1, 2031<svg><main></main></svg>"
        " and June 30, 2031</p>",
        "<p>w0<svg><address></address></svg>w1</p>",
        "<p>w0<svg><dir></dir></svg>w1</p>",
        "<p>w0<svg><form></form></svg>w1</p>",
        "<p>w0<svg><header></header></svg>w1</p>",
        "<p>w0<svg><summary></summary></svg>w1</p>",
        "<p>w0<svg><xmp>w1</xmp></svg>w2</p>",
        "<p>w0<SVG><Section></Section></SVG>w1</p>",
        "<p>w0<math><svg><section></section></svg></math>w1</p>",
        # HTML's breakout tags, foreign-content HTML and svg or MathML
        # elements outside the vocabulary, over-refusals the tree's
        # docstring names.
        "<svg><h3>Utah</h3></svg>",
        "<p>w0<svg><b>w1</b></svg>w2</p>",
        "<svg><foreignObject><p>w0</p></foreignObject></svg>",
        "<p>w0<math><mi><b>w1</b></mi></math>w2</p>",
        "<p>w0<svg><a>w1</a></svg>w2</p>",
        "<p>w0<math><mover></mover></math>w1</p>",
    ],
)
def test_invented_html_element_inside_svg_or_math_refuses_the_page(
    fragment,
):
    """Regression (the round-12 review's Low 2): the tree built these as
    HTML blocks inside the svg or math, where HTML keeps them foreign, so
    a date, State or claimant dropped out of its block. Only svg and
    MathML elements may start inside svg or math."""
    with pytest.raises(TableStructureError, match="starts inside svg or"):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_cell_inside_svg_in_a_chart_refuses_the_page():
    """The review's chart row: a td inside an svg in the category cell
    moved the row's amounts one column on, so "State Supplement Level"
    took the FBR column's amount, with no flag."""
    page, end, after = invented_nevada_with("").rpartition(b"</table>")
    payload = (
        page + b"<tr><td>A</td><td>B</td><td>Invented<svg><td></svg></td>"
        b"<td>11</td><td>22</td><td>33</td></tr>" + end + after
    )
    with pytest.raises(TableStructureError, match="starts inside svg or"):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's minimized differential page: html5lib ignores the
        # </h5> inside mi, so the h5 holds the date.
        "<h5><math><mi></h5>and June 30, 2031",
        "<h5><svg><desc></h5>and June 30, 2031",
        "<p>Payment levels effective March 1, 2031<svg><desc></p>and June"
        " 30, 2031",
        # An end tag of an element outside, and svg or math left open at
        # the end of the page.
        "<p>w0<svg></p></svg>w1</p>",
        "<div>w0<svg></div></svg>",
        "<p>w0<math><svg></math>w1</p>",
        "<p>w0<svg><math></svg>w1</p>",
    ],
)
def test_invented_svg_or_math_ended_by_another_end_tag_refuses_the_page(
    fragment,
):
    with pytest.raises(TableStructureError, match="its own end tag"):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize("fragment", ["<p>w0<svg><path/>", "<math><mi>w0"])
def test_invented_svg_or_math_left_open_refuses_the_page(fragment):
    payload = invented_nevada_with("") + fragment.encode()
    with pytest.raises(TableStructureError, match="its own end tag"):
        describe_poms_tables(payload)


@pytest.mark.parametrize(
    "fragment",
    [
        # svg and MathML elements, in any case, nested, and closed by the
        # svg's end tag.
        "<p>w0<svg><g><rect></svg>w1</p>",
        "<p>w0<SVG><PATH/></SVG>w1</p>",
        "<p>w0<math><svg><path/></svg></math>w1</p>",
        "<p>w0<svg><foreignObject>w1</foreignObject></svg>w2</p>",
        "<p>w0<math><mi>w1</mi><mo>w2</mo><mn>1</mn></math>w3</p>",
    ],
)
def test_invented_svg_and_math_vocabulary_is_read(fragment):
    assert invented_selector(invented_nevada_with(fragment)) == (
        "Nevada",
        "individual",
        "2030-01-01",
        [0],
    )


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's FB1 to FB8: a leading sup or link whose text is a
        # word of a marker's size made a footnote body.
        "<p><sup>As of</sup> March 1, 2031</p>",
        "<h5><a href='#new'>New</a> payment levels as of March 1, 2031</h5>",
        "<h5><sup>*</sup>Payment levels as of March 1, 2031</h5>",
        "<p><sup>Now</sup> payment levels as of March 1, 2031</p>",
        "<p><sup>Pay</sup>ment levels as of March 1, 2031</p>",
        "<p><a href='notes.html#fn1'>All</a> payment levels as of March 1,"
        " 2031</p>",
        "<p><a href='#a'>See</a> 2031 payment levels</p>",
        "<p><sup>In</sup> 2031 payment levels rise</p>",
    ],
    ids=["FB1", "FB2", "FB3", "FB4", "FB5", "FB6", "FB7", "FB8"],
)
def test_invented_leading_word_makes_no_footnote_body(fragment):
    """Regression (the round-12 review's Low 3): any word of one to three
    characters in a leading sup or footnote link made the line a footnote
    body, which dates no chart. Its words must now be one to three digits
    or footnote signs, or a single letter, and a heading is never a
    footnote body."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with(fragment))


@pytest.mark.parametrize(
    "marker",
    [
        "<sup>1</sup>",
        "<sup>*</sup>",
        "<sup>a</sup>",
        "<sup>12</sup>",
        "<sup>†</sup>",
        "<a href='#fn2'>2</a>",
    ],
)
def test_invented_footnote_body_between_charts_still_dates_nothing(marker):
    *_, last = describe_poms_tables(
        invented_after_a_chart(
            f"<p>{marker}Revised March 1, 2031</p><h4>Couple</h4>"
        )
    )
    assert (last["claimant_type"], last["effective_from"]) == (
        "couple",
        "2030-01-01",
    )


@pytest.mark.parametrize(
    "fragment",
    [
        # Over-refusals the Limits list names: a marker of two letters or
        # a digit and a letter, and a heading that opens with a marker.
        "<p><sup>ii</sup>Revised March 1, 2031</p>",
        "<p><sup>1a</sup>Revised March 1, 2031</p>",
        "<h5><sup>1</sup>Revised March 1, 2031</h5>",
    ],
)
def test_invented_other_leading_markers_leave_the_date_unread(fragment):
    with pytest.raises(TableStructureError, match="table 2 follows a date"):
        describe_poms_tables(
            invented_after_a_chart(f"{fragment}<h4>Couple</h4>")
        )


@pytest.mark.parametrize(
    "fragment",
    [
        # The review's Note 3: a footnote line naming the split date, a
        # comma after the br, and a heading's footnote marker.
        "<p>Payment levels as of March 1,<br>2031<br><sup>1</sup>Revised"
        " March 1, 2031</p>",
        "<p>Payment levels as of March 1<br>, 2031</p>",
        "<h5><sup>1</sup>Note<br>Payment levels as of March 1, 2031</h5>",
        # A split date only the bare reading shows.
        "<p>Payment levels as of March 1,<br>20<sup>1</sup>31</p>",
    ],
)
def test_invented_split_or_heading_date_beside_a_footnote_is_unread(fragment):
    """Regression (the round-12 review's Note 3): in a section dated
    January 1, 2031, a footnote line that named the same date covered a
    date split across a br, a comma after a br hid the split date, and a
    heading that opened with a marker was a footnote body. The whole text
    now adds the dates it names more often than its lines do, "Month d ,
    yyyy" names a date, and a heading is never a footnote body."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_2031_with(fragment))


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        # Limits the docstring names: a date split across two blocks, and
        # a long date sentence whose second date takes another form.
        ("<p>Payment levels as of March 1,</p><p>2031</p>", "2031-01-01"),
        (
            "<p>Payment levels effective March 1, 2031 and July 1st, 2031"
            f"{INVENTED_LONG_TAIL}</p>",
            "2031-03-01",
        ),
    ],
)
def test_invented_date_limits_leave_the_date_standing(fragment, expected):
    assert invented_selector(invented_nevada_2031_with(fragment))[2] == (
        expected
    )


@pytest.mark.parametrize(
    "line",
    [
        # The review's Note 4, and the revision range in any case.
        "effective dates: 03/01/2031 - present",
        "Effective dates: 03/01/2031 - Present",
        "EFFECTIVE DATES: 03/01/2031 - PRESENT",
    ],
)
def test_invented_revision_range_in_any_case_dates_no_chart(line):
    """Regression (the round-12 review's Note 4): the revision range and
    the date sentence's exclusion of it were case-sensitive, so a
    lower-case "Effective dates:" line dated the chart March 1, 2031."""
    payload = invented_nevada_with(f"<p>{line}</p>").replace(
        b"<p>Effective Dates: 02/03/2040 - Present</p>", b""
    )
    (context,) = describe_poms_tables(payload)
    assert (
        context["effective_from"],
        context["section_effective_from"],
        context["section_effective_to"],
    ) == ("2030-01-01", "2031-03-01", None)


def test_invented_lower_case_revision_range_keeps_its_end():
    payload = invented_nevada_with(
        "<p>effective dates: 03/01/2031 - 04/01/2031</p>"
    ).replace(b"<p>Effective Dates: 02/03/2040 - Present</p>", b"")
    (context,) = describe_poms_tables(payload)
    assert (
        context["effective_from"],
        context["section_effective_from"],
        context["section_effective_to"],
    ) == ("2030-01-01", "2031-03-01", "2031-04-01")


@pytest.mark.parametrize(
    ("date", "message"),
    [
        # Q4: the second of two ranges does not end after it starts.
        (
            "from March 1, 2031 to June 30, 2031, and effective from July 1,"
            " 2031 to March 1, 2031",
            "range does not end after it starts",
        ),
        # Q5: a link of a marker's size, with no href, inside a date.
        (
            "January 1<a name='n5'>5</a>, 2031",
            "reads differently without its footnote markers",
        ),
    ],
    ids=["Q4", "Q5"],
)
def test_invented_round_12_review_date_witnesses_are_refused(date, message):
    """The round-12 review's Low 4: the witnesses of its surviving mutants
    Q4 and Q5, each in the section's date sentence."""
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_dated(date))


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        # Q8: a leading link elsewhere of a marker's size, which only the
        # unlinked reading drops, makes no footnote body; and the review's
        # own witness, which the footnote-word rule refuses too.
        (
            "<p><a href='x.html'>1</a> payment levels as of March 1,"
            " 2031</p>",
            "no effective-date sentence states",
        ),
        (
            "<p><a href='x.html'>New</a> payment levels as of March 1,"
            " 2031</p>",
            "no effective-date sentence states",
        ),
        # Q9: self-closed raw text and RCDATA tags with attributes, the
        # common real form.
        (
            "<script src='x.js'/><h3>Utah</h3><h4>Couple</h4></script>",
            "self-closed raw text",
        ),
        (
            "<style media='print'/><h3>Utah</h3><h4>Couple</h4></style>",
            "self-closed raw text",
        ),
        (
            "<title lang='en'/><h3>Utah</h3><h4>Couple</h4></title>",
            "self-closed raw text",
        ),
    ],
    ids=["Q8", "Q8-review", "Q9", "Q9-style", "Q9-title"],
)
def test_invented_round_12_review_witnesses_are_refused(fragment, message):
    """The round-12 review's Low 4: the witnesses of its surviving mutants
    Q8 and Q9."""
    with pytest.raises(TableStructureError, match=message):
        describe_poms_tables(invented_nevada_with(fragment))


def test_invented_heading_year_of_a_second_date_in_force_is_read():
    """The round-12 review's Q1 witness: with two dates in force, a heading
    that holds the later one's year leaves both standing as named
    alternatives."""
    payload = invented_nevada_with("<h5>2031 levels</h5>").replace(
        b"effective January 1, 2030",
        b"effective January 1, 2030 and January 1, 2031",
        1,
    )
    (context,) = describe_poms_tables(payload)
    assert context["effective_from"] is None
    assert context["date_options"] == {
        "source_date_1": "2030-01-01",
        "source_date_2": "2031-01-01",
    }


def test_invented_line_of_two_revision_ranges_dates_no_chart():
    """The round-12 review's Q11 witness: the net drops every revision range
    from a line, so a line holding two dates no chart."""
    payload = invented_nevada_with(
        "<p>Effective Dates: 03/01/2031 - Present Effective Dates:"
        " 04/01/2031 - Present</p>"
    )
    assert invented_selector(payload)[2] == "2030-01-01"


def test_invented_heading_earlier_year_without_a_dating_word_is_unread():
    """A heading counts a year outside the dates in force whatever words it
    holds. The review's Q12, ported, counts an h5's earlier year only with
    a dating word, so this h5 reads under it."""
    with pytest.raises(TableStructureError, match="no effective-date sent"):
        describe_poms_tables(invented_nevada_with("<h5>Notes for 2029</h5>"))
