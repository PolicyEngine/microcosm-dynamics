"""Prove the published d1408 diagnostic reveals no group under ten.

Verification class: labelled diagnostic publication guard. The committed
JSON is read as an aggregate artifact; no microdata is opened. The
guarantee is that no signed (+1/-1) combination, of any size, of the
distinct published populations within a population family, people and
worker-record counts pooled together, equals one through nine. Every
positive count declares the population it measures; a population
republished in several cells enters once and must match. Each family
publishes at most ``MAX_CELLS`` distinct populations, so the committed
JSON is also checked by listing all 3**n sign patterns outright. The
invented-input properties show that the sweep finds every planted small
combination and agrees with brute force, and the regressions replay the
three differencing routes found in review round 1 (COLA rows, nested role
subtotals, Track M's two readings) on seeded synthetic aggregates from
``tests/d1408_synthetic.py``.
"""

import itertools
import json
import re
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from scripts import d1408_diagnostic
from scripts.d1408_publication_view import (
    FAMILIES,
    MAX_CELLS,
    PEOPLE_KEYS,
    RECORD_KEYS,
    differencing_violations,
    distinct_cells,
    minimum_view,
    path_category,
    projection_view,
    published_cells,
    published_counts,
    reachable_sums,
)
from tests import d1408_synthetic as synthetic

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = (
    ROOT / "docs/errata/2026-10-11-delayed-credit-window-diagnostic.json"
)
ERRATUM = ROOT / "docs/errata/2026-10-11-delayed-credit-window.md"
FIRST_ESTIMATES = ROOT / "runs/first_estimates_v1.json"


def _document():
    return json.loads(PUBLISHED.read_text())


def _count_leaves(value):
    """Independently count integer leaves under count keys; none exempt."""
    total = 0
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                key in PEOPLE_KEYS | RECORD_KEYS
                and isinstance(item, int)
                and not isinstance(item, bool)
            ):
                total += 1
            else:
                total += _count_leaves(item)
    elif isinstance(value, list):
        total += sum(_count_leaves(item) for item in value)
    return total


def test_every_published_subtraction_is_zero_negative_or_at_least_ten():
    document = _document()
    cells = list(published_counts(document))
    # The walker sees every published count, across every row, wave and
    # Track M reading; none is skipped.
    assert len(cells) == _count_leaves(document)
    paths = [path for _, _, path, _ in cells]
    assert any("headline_changes" in path for path in paths)
    assert any("readings/scored" in path for path in paths)
    assert any("readings/d430_sensitivity" in path for path in paths)
    # Brute force over every sign pattern of every pool's distinct sets,
    # recomputed here rather than trusted, and checked against the sweep.
    pools = distinct_cells(document)
    assert pools
    for family, cells in pools.items():
        assert len(cells) <= MAX_CELLS
        values = [cell["value"] for cell in cells]
        brute = {
            sum(c * v for c, v in zip(coefs, values, strict=True))
            for coefs in itertools.product((-1, 0, 1), repeat=len(values))
        }
        assert set(reachable_sums(values)) == brute
        assert not brute & set(range(1, 10)), (family, values)
    assert differencing_violations(document) == []


def test_every_positive_count_declares_its_population():
    document = _document()
    cells = list(published_cells(document))
    assert cells
    for _, _, path, value, _, population in cells:
        if value > 0:
            assert isinstance(population, str) and population, path
    # R7 and cost ordering are one frame: the shared ids carry identical
    # cells (distinct_cells raises otherwise).
    pools = distinct_cells(document)
    shared = {
        (cell["population"], cell["unit"]): len(cell["paths"])
        for cell in pools["r7"]
    }
    assert shared == {
        ("r7_frame/admitted", "people"): 2,
        ("r7_frame/flagged_supported", "people"): 2,
        ("r7_frame/flagged_supported", "worker_records"): 2,
    }
    # Every other population is published once.
    for family, cells in pools.items():
        if family != "r7":
            assert all(len(cell["paths"]) == 1 for cell in cells), family
    # Track M's flagged people include linked beneficiaries, so its flagged
    # worker-record count is not published (round 3).
    (minimum,) = [
        r
        for r in document["results"]
        if r["result"] == "track_m_minimum_benefit"
    ]
    flagged = minimum["readings"]["scored"]["flagged_supported"]
    assert "worker_records" not in flagged


def test_no_published_count_is_a_small_cell():
    for _, _, path, value in published_counts(_document()):
        assert value == 0 or value >= 10, path


def test_every_family_is_pooled():
    families = {family for family, *_ in published_counts(_document())}
    assert families == set(FAMILIES.values())


def test_no_count_is_exempt_and_bound_shares_use_committed_weights():
    text = PUBLISHED.read_text()
    assert "committed_admitted_denominators" not in text
    committed = FIRST_ESTIMATES.read_text()
    (first,) = [
        r for r in _document()["results"] if r["result"] == "first_estimates"
    ]
    bound = first["counts"]["actual_person_upper_bound"]["weight"]
    shares = first["counts"]["upper_bound_shares_by_draw"]
    assert len(shares) == 20
    for row in shares:
        weight = bound / row["admitted_weight_share_upper_bound"]
        assert abs(weight - round(weight)) < 1e-4, row
        assert re.search(rf"\b{round(weight)}(\.0)?\b", committed), row


def test_erratum_table_publishes_nothing_beyond_the_json():
    text = ERRATUM.read_text()
    section = text[text.index("## The d1408 diagnostic") :]
    section = section[: section.index("\n## ", 5)]
    table = [line for line in section.splitlines() if line.startswith("|")]
    published = set()
    for _, _, _, value in published_counts(_document()):
        published.add(int(value))

    def numbers(value):
        if isinstance(value, dict):
            for item in value.values():
                yield from numbers(item)
        elif isinstance(value, list):
            for item in value:
                yield from numbers(item)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            yield value

    weights = {int(v) for v in numbers(_document()) if float(v).is_integer()}
    for line in table:
        # Age-group labels (50–61, 80+) are adjacent to a dash or plus.
        pattern = r"(?<![\w.%–])\d[\d,]*(?![\d.%–+]|\w)"
        # The first column names the result (for example "FRA 68").
        counted = "|".join(line.split("|")[2:])
        for token in re.findall(pattern, counted):
            value = int(token.replace(",", ""))
            if value < 10 or 1900 <= value <= 2100:
                continue  # single digits and years
            assert value in published | weights, (token, line)


# ---- invented-input properties of the enumeration ----


def _invented(counts):
    return {
        "results": [
            {
                "result": "cola",
                "waves": {
                    str(index): {
                        "flagged_supported": {
                            "people": value,
                            "population": f"invented/{index}",
                        }
                    }
                    for index, value in enumerate(counts)
                },
            }
        ]
    }


_SPACED = st.lists(
    st.integers(min_value=0, max_value=400), min_size=1, max_size=6
).map(lambda xs: sorted({10 * x + 10 for x in xs}))


@settings(deadline=None, max_examples=200)
@given(_SPACED, st.integers(1, 9), st.integers(1, 6), st.randoms())
def test_planted_small_difference_is_found(base, small, subtrahends, rnd):
    # A total equal to `small` plus any number of distinct published
    # subtotals: the sweep has no size limit.
    parts = rnd.sample(base, min(subtrahends, len(base)))
    counts = base + [small + sum(parts)]
    rnd.shuffle(counts)
    violations = differencing_violations(_invented(counts))
    assert any(v["value"] == small for v in violations)
    witness = next(v for v in violations if v["value"] == small)
    assert witness["terms"]


@settings(deadline=None, max_examples=300)
@given(st.lists(st.integers(0, 400), min_size=0, max_size=9))
def test_sweep_equals_brute_force_over_every_sign_pattern(values):
    brute = {
        sum(c * v for c, v in zip(coefs, values, strict=True))
        for coefs in itertools.product((-1, 0, 1), repeat=len(values))
    }
    reached = reachable_sums(values)
    assert set(reached) == brute
    for total, witness in reached.items():
        assert sum(sign * values[i] for i, sign in witness) == total
        assert len({i for i, _ in witness}) == len(witness)


def test_pool_beyond_the_bound_refuses():
    counts = [10 * (k + 1) for k in range(MAX_CELLS + 1)]
    with pytest.raises(ValueError, match="full differencing sweep"):
        differencing_violations(_invented(counts))
    assert differencing_violations(_invented(counts[:MAX_CELLS])) == []


def _rows(*cells):
    return {
        "results": [
            {
                "result": "cola",
                "rows": {
                    f"r{i}": {
                        "people": people,
                        "weight": weight,
                        "population": population,
                    }
                    for i, (people, weight, population) in enumerate(cells)
                },
            }
        ]
    }


def test_declared_population_enters_once_and_must_match():
    a, b = synthetic.counts("declared-population", 2)
    w1, w2 = synthetic.weights("declared-population", 2)
    same = _rows((a, w1, "denominator"), (a, w1, "denominator"))
    assert len(distinct_cells(same)["projection"]) == 1
    with pytest.raises(ValueError, match="does not match"):
        distinct_cells(_rows((a, w1, "d"), (a - 9, w1, "d")))
    with pytest.raises(ValueError, match="does not match"):
        distinct_cells(_rows((a, w1, "d"), (a, w2, "d")))
    # Different populations never merge, even with equal count and weight.
    twins = _rows((a, w1, "a"), (a, w1, "b"), (2 * a - 9, w1, "c"))
    assert len(distinct_cells(twins)["projection"]) == 3
    assert 9 in {v["value"] for v in differencing_violations(twins)}
    unweighted = _invented([b, b, 2 * b + 5])
    assert [v["value"] for v in differencing_violations(unweighted)] == [5]


def test_count_without_a_population_refuses():
    (count,) = synthetic.counts("no-population", 1)
    document = {"results": [{"result": "cola", "w": {"people": count}}]}
    with pytest.raises(ValueError, match="without a population"):
        differencing_violations(document)


@settings(deadline=None, max_examples=200)
@given(st.lists(st.integers(0, 300), min_size=1, max_size=6), st.randoms())
def test_counts_spaced_by_at_least_ten_never_violate(multiples, rnd):
    # Multiples of ten: every signed sum is a multiple of ten.
    counts = [10 * m for m in multiples]
    rnd.shuffle(counts)
    assert differencing_violations(_invented(counts)) == []


@settings(deadline=None)
@given(_SPACED, st.integers(1, 9), st.randoms())
def test_enumeration_is_order_independent(base, small, rnd):
    counts = base + [base[0] + small]
    shuffled = list(counts)
    rnd.shuffle(shuffled)
    values = sorted(
        v["value"] for v in differencing_violations(_invented(counts))
    )
    again = sorted(
        v["value"] for v in differencing_violations(_invented(shuffled))
    )
    assert values == again and small in values


def test_units_pool_together_but_families_do_not():
    # People and worker records of one family are differenced together:
    # people minus records equal to six is a violation (round 3's route).
    people, other = synthetic.counts("unit-pooling", 2)
    same_family = {
        "results": [
            {
                "result": "cola",
                "waves": {"2011": {"people": people, "population": "a"}},
            },
            {
                "result": "fra68",
                "w": {"worker_records": people - 6, "population": "c"},
            },
        ]
    }
    assert [v["value"] for v in differencing_violations(same_family)] == [6]
    other_family = {
        "results": [
            {
                "result": "cola",
                "waves": {"2011": {"people": people, "population": "a"}},
            },
            {
                "result": "r7_sharing",
                "flagged": {"people": people - 6, "population": "b"},
            },
        ]
    }
    assert differencing_violations(other_family) == []


# ---- regressions for review round 1's three routes ----


def _declare_by_path(value, path="raw"):
    """Give every raw cell its own population, the strictest pooling."""
    if isinstance(value, dict):
        out = {k: _declare_by_path(v, f"{path}/{k}") for k, v in value.items()}
        if any(
            k in PEOPLE_KEYS | RECORD_KEYS and isinstance(v, int)
            for k, v in out.items()
        ):
            out["population"] = path
        return out
    if isinstance(value, list):
        return [
            _declare_by_path(v, f"{path}/{i}") for i, v in enumerate(value)
        ]
    return value


def _cell(people, records, weight):
    return {
        "people": people,
        "worker_records": records,
        "weight": weight,
        "admitted_weight_share": weight / 1e6,
    }


def _invented_projection():
    # Seeded synthetic values (tests/d1408_synthetic.py): nested row and
    # role subtotals whose differences are 4, 1, 2 and 5, the shape of
    # review round 1's routes.
    flagged, deceased, spouse, row_factor, row_spouse, r0, r5 = (
        synthetic.counts("projection", 7)
    )
    w = synthetic.weights("projection", 11)
    wave = {
        "seed_cohort_weight": w[0],
        "denominator": "invented",
        "supported/factor_evaluation": _cell(flagged, flagged, w[1]),
        "supported/deceased_auxiliary_basis": _cell(deceased, deceased, w[2]),
        "supported/positive_survivor_payment": _cell(
            deceased - 5, deceased - 5, w[3]
        ),
        "supported/linked_spouse_basis": _cell(spouse, spouse, w[4]),
    }
    row = {
        "admitted_people": r0,
        "admitted_weight": w[5],
        "supported/factor_evaluation": _cell(row_factor, row_factor - 3, w[6]),
        "supported/linked_spouse_basis": _cell(row_spouse, row_spouse, w[7]),
    }
    restricted = {
        "admitted_people": r5,
        "admitted_weight": w[8],
        "supported/factor_evaluation": _cell(
            row_factor - 4, row_factor - 4, w[9]
        ),
        "supported/linked_spouse_basis": _cell(
            row_spouse - 2, row_spouse - 2, w[10]
        ),
    }
    return {
        "result": "cola",
        "artifact": "runs/replication_urban2010_cola_v1.json",
        "counts": {"2011": wave},
        "admitted_beneficiary_counts_by_row": {"R0": row, "R5": restricted},
        "headline_changes": {},
    }


def test_round1_row_and_role_routes_are_present_raw_and_gone_public():
    raw = _invented_projection()
    raw_doc = {"results": [_declare_by_path(raw)]}
    # The raw aggregate leaks exactly as the review found.
    leaked = {v["value"] for v in differencing_violations(raw_doc)}
    assert {4, 1, 2, 5} <= leaked
    public = {"results": [projection_view(raw)]}
    assert differencing_violations(public) == []
    # No row attribution subtotal or row denominator is published.
    assert "admitted_by_row" not in public["results"][0]
    assert "admitted_beneficiary_counts_by_row" not in public["results"][0]
    paths = public["results"][0]["waves"]["2011"]["paths"]
    assert paths["deceased_auxiliary_basis"] == "ten or more"
    assert paths["positive_survivor_payment"] == "ten or more"
    assert paths["own_record"] == "none"
    # One record per person: the fact is published, not a second count.
    flagged = public["results"][0]["waves"]["2011"]["flagged_supported"]
    assert flagged["one_worker_record_per_person"] is True
    assert "worker_records" not in flagged
    assert "seed_cohort_weight_share" in flagged
    assert "admitted_weight_share" not in flagged


(
    _TRACK_M_ADMITTED,
    _TRACK_M_RECORDS,
    _TRACK_M_FLAGGED,
    _TRACK_M_FLAGGED_RECORDS,
) = synthetic.counts("track-m", 4)
_TRACK_M_WEIGHT, _TRACK_M_FLAGGED_WEIGHT = synthetic.weights("track-m", 2)


def _track_m_flagged():
    return _cell(
        _TRACK_M_FLAGGED, _TRACK_M_FLAGGED_RECORDS, _TRACK_M_FLAGGED_WEIGHT
    )


def _reading(records, flagged):
    zero = {
        "admitted_people": _TRACK_M_ADMITTED,
        "admitted_weight": _TRACK_M_WEIGHT,
        "changed_receiving_people": 0,
        "supported_subset_change_percentage_points": 0.0,
        "change_in_admitted_people": 0,
    }
    small = {"people": "<10", "worker_records": "<10", "weight": "<10"}
    return {
        "admitted_people": _TRACK_M_ADMITTED,
        "admitted_worker_records": records,
        "admitted_weight": _TRACK_M_WEIGHT,
        "supported": {
            "all_flagged_evaluations": flagged,
            "admitted_flagged_worker_owners": small,
            "linked_auxiliary_basis": small,
            "factor_entered_survivor_payment_gate": small,
            "factor_entered_inverse_ms5_pia": small,
        },
        "pre1917_unsupported": {"all_flagged_evaluations": {"people": 0}},
        "rows": {
            "MS0": {
                "changes": {"option_2/all": zero},
                "legacy_reproduction": {"option_2/all": {"exact_match": True}},
            }
        },
        "legacy_reproduction_verified": True,
    }


def test_round1_track_m_reading_route_is_present_raw_and_gone_public():
    raw = {
        "result": "track_m_minimum_benefit",
        "readings": {
            "scored": _reading(_TRACK_M_RECORDS, _track_m_flagged()),
            "d430_sensitivity": _reading(
                _TRACK_M_RECORDS - 6,
                {
                    "people": "suppressed_complementary",
                    "worker_records": "suppressed_complementary",
                },
            ),
        },
    }
    leaked = {
        v["value"]
        for v in differencing_violations({"results": [_declare_by_path(raw)]})
    }
    assert 6 in leaked
    public = minimum_view(raw)
    assert "admitted" not in public["readings"]["d430_sensitivity"]
    # Round 3: people (with linked beneficiaries) minus flagged records
    # would bound a withheld cell, so the flagged record count is dropped.
    scored_flagged = public["readings"]["scored"]["flagged_supported"]
    assert scored_flagged["people"] == _TRACK_M_FLAGGED
    assert "worker_records" not in scored_flagged
    assert (
        public["readings"]["scored"]["admitted"]["worker_records"]
        == _TRACK_M_RECORDS
    )
    assert public["readings"]["d430_sensitivity"]["flagged_supported"] == (
        "withheld"
    )
    assert differencing_violations({"results": [public]}) == []


def test_nonzero_track_m_change_is_refused_not_summarized():
    reading = _reading(_TRACK_M_RECORDS, _track_m_flagged())
    reading["rows"]["MS0"]["changes"]["option_2/all"][
        "supported_subset_change_percentage_points"
    ] = 0.1
    with pytest.raises(ValueError, match="nonzero Track M change"):
        minimum_view(
            {
                "result": "track_m_minimum_benefit",
                "readings": {"scored": reading},
            }
        )


_THRESHOLD = 10  # the small-cell threshold, not a fixture count


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        (None, "none"),
        ({"people": 0}, "none"),
        ({"people": 1}, "fewer than ten"),
        ({"people": _THRESHOLD - 1}, "fewer than ten"),
        ({"people": _THRESHOLD}, "ten or more"),
        ({"people": "<10"}, "fewer than ten"),
        ({"people": "suppressed_complementary"}, "withheld"),
    ],
)
def test_path_category_never_publishes_a_count(cell, expected):
    assert path_category(cell) == expected


(_FAKE,) = synthetic.counts("assembler", 1)


def test_assembler_refuses_a_document_with_a_small_difference(monkeypatch):
    def fake(results):
        return {
            "result": results["result"],
            "waves": {
                "a": {"people": _FAKE, "population": "a"},
                "b": {"people": _FAKE - 3, "population": "b"},
            },
        }

    monkeypatch.setattr(d1408_diagnostic, "public_view", fake)
    monkeypatch.setattr(d1408_diagnostic, "validate_result_scope", lambda r: 0)
    monkeypatch.setattr(
        d1408_diagnostic, "validate_projection_publication", lambda r: 0
    )
    monkeypatch.setattr(d1408_diagnostic, "DESTINATION", Path("/dev/null/x"))

    class Scratch:
        def __truediv__(self, name):
            return _Aggregate(name)

    class _Aggregate:
        def __init__(self, name):
            self.name = name

        def is_file(self):
            return True

        def read_text(self):
            if "sharing" in self.name:
                return json.dumps({"results": [{"result": "r7_sharing"}]})
            return json.dumps({"result": "cola"})

    monkeypatch.setattr(d1408_diagnostic, "SCRATCH", Scratch())
    with pytest.raises(ValueError, match="reveal a group under ten"):
        d1408_diagnostic.assemble()


def test_republishing_first_estimates_draw_denominators_is_refused():
    # Round 2: two draws' admitted counts that differ by one person would
    # make a difference of one if both were republished.
    document = _document()
    (first,) = [
        r for r in document["results"] if r["result"] == "first_estimates"
    ]
    (draw,) = synthetic.counts("draw-denominators", 1)
    w1, w2 = synthetic.weights("draw-denominators", 2)
    rows = [
        {"draw_index": 1, "people": draw, "weight": w1},
        {"draw_index": 11, "people": draw - 1, "weight": w2},
    ]
    first["counts"]["draw_denominators"] = rows
    with pytest.raises(ValueError, match="without a population"):
        differencing_violations(document)
    for row in rows:
        row["population"] = f"first_estimates/draw{row['draw_index']}"
    assert 1 in {v["value"] for v in differencing_violations(document)}
