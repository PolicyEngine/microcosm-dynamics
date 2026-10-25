"""Invented HTML only; no public or person data supply these fixtures."""

import string
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.aggregate_poms import (
    _own_text,
    _payment_rows,
    describe_poms_tables,
    parse_poms,
    poms_code_alternatives,
    poms_living_arrangements,
)
from populace_dynamics.income_resources.aggregate_tables import (
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
@given(st.lists(st.integers(0, 999999), min_size=2, max_size=4))
def test_invented_stacked_layout_preserves_each_amount(amounts):
    paragraphs = "".join(
        f"<p>{amount:,}<sup>x</sup></p>" for amount in amounts
    )
    labels = "".join(
        f"<p>Category {index}</p>" for index in range(len(amounts))
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
        pieces.append(
            ("p", heading)
            if draw(st.booleans())
            else ("html", f"<h3>{heading}</h3>")
        )
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


def invented_rendering(pieces, closed) -> bytes:
    return invented_payload(
        *(
            f"<p>{body}" + ("</p>" if close else "") if kind == "p" else body
            for (kind, body), close in zip(pieces, closed, strict=True)
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
