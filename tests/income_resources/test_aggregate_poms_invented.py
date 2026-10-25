"""Invented HTML only; no public or person data supply these fixtures."""

import string
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.aggregate_poms import (
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
    block = next(parse_html(f"<{tag}>{inline}</{tag}>").iter(tag))
    assert _own_text(block) == normalized_text(block)


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
    """Each start tag that ends an open paragraph in HTML ends it here."""
    assert set(SPEC_PARAGRAPH_CLOSERS) == PARAGRAPH_CLOSERS
    for closer in SPEC_PARAGRAPH_CLOSERS:
        # Text inside the closer would join the heading if it did not end it.
        block = (
            "<hr>Invented note"
            if closer == "hr"
            else f"<{closer}>Invented note</{closer}>"
        )
        for close in ("", "</p>"):
            spec, _ = invented_spec_for(
                invented_nevada_after_california(f"<p>Nevada{close}{block}"),
                1,
            )
            assert spec.selector["state"] == "Nevada", closer
            assert spec.selector["definitions_table_indexes"] == [], closer


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
