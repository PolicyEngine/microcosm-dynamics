"""Invented HTML only; no public or person data supply these fixtures."""

import string
import subprocess
import sys
import unicodedata
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.aggregate_poms import (
    _STATES,
    _blank,
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


def test_invented_unrelated_program_prose_does_not_replace_chart_date():
    spec, payload = invented_spec(
        "<tr><td>A</td><td>A</td><td>All</td>"
        "<td>100</td><td>10</td><td>110</td></tr>"
    )
    payload = payload.replace(
        b"<h4>a. Individual payment levels for California</h4>",
        b"<p>A separate invented program was effective August 2029.</p>"
        b"<h4>a. Individual payment levels for California</h4>",
    )
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


def test_invented_washington_dc_names_the_district():
    payload = invented_payload(
        invented_section(
            "District of Columbia", [[("A", "Invented first")]]
        ).replace(
            "a. Individual payment levels for District of Columbia",
            "Individual or couple for Washington, D.C.",
        )
    )
    (context,) = describe_poms_tables(payload)
    assert context["state"] == "District of Columbia"
    assert context["claimant_type"] == "individual"


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
        # A paragraph that names another State is prose, not a heading.
        "<p>Invented note on Nevada</p>",
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
