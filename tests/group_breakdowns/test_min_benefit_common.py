"""The shared pieces of the group-breakdown adapters (NASI G4c).

Unit tier: everything here is INVENTED or synthetic, and nothing reads a
PSID file or a committed artifact.  The exact comparison
(:func:`common.compare_exact`) is load-bearing: it is what stops a
breakdown before any group attribute is read, so its invariants are
property-tested:

* a document compared with itself has no difference, and every leaf is
  compared;
* moving any one leaf (a float by one unit in the last place, an integer
  by one, a string, a sign of zero) is found, at exactly that leaf's path;
* the refusal names paths only, never a value.
"""

from __future__ import annotations

import copy
import json
import math
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cohorts import group_attributes as g1
from populace_dynamics.data import group_attributes_psid as gap
from populace_dynamics.estimates import group_breakdown as g3
from populace_dynamics.group_breakdowns import common
from populace_dynamics.min_benefit_track_m import DRY_RUN_HEADER
from populace_dynamics.track_a_v2 import INVENTED_HEADER

# -------------------------------------------------------------------------
# Strategies: JSON documents as the registered runners write them
# -------------------------------------------------------------------------
_LEAVES = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**12), max_value=10**12),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=8),
)
_DOCUMENTS = st.recursive(
    _LEAVES,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(min_size=1, max_size=6), children, max_size=4),
    ),
    max_leaves=25,
)


def _leaf_paths(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        out = []
        for key in sorted(value, key=str):
            out.extend(_leaf_paths(value[key], f"{path}.{key}"))
        return out
    if isinstance(value, list):
        out = []
        for index, item in enumerate(value):
            out.extend(_leaf_paths(item, f"{path}[{index}]"))
        return out
    return [(path, value)]


def _set(document: Any, path: str, new: Any) -> Any:
    """``document`` with the leaf at ``path`` replaced (paths as above)."""

    out = copy.deepcopy(document)
    for candidate, _ in _leaf_paths(out):
        if candidate != path:
            continue
        holder: Any = None
        key: Any = None
        node: Any = out
        tokens = _tokens(path)
        for token in tokens:
            holder, key = node, token
            node = node[token]
        if holder is None:
            return new
        holder[key] = new
        return out
    raise KeyError(path)


def _tokens(path: str) -> list[Any]:
    tokens: list[Any] = []
    rest = path[1:]
    while rest:
        if rest.startswith("["):
            end = rest.index("]")
            tokens.append(int(rest[1:end]))
            rest = rest[end + 1 :]
        else:
            rest = rest[1:]
            cut = min(
                [i for i in (rest.find("."), rest.find("[")) if i >= 0]
                or [len(rest)]
            )
            tokens.append(rest[:cut])
            rest = rest[cut:]
    return tokens


def _moved(value: Any) -> Any:
    """A leaf one step away from ``value``, of the same JSON type."""

    if value is None:
        return 0
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        if value == 0.0:
            return -value if math.copysign(1.0, value) > 0 else 0.0
        up = math.nextafter(value, math.inf)
        return up if math.isfinite(up) else math.nextafter(value, -math.inf)
    return value + "x"


def _simple_keys(document: Any) -> bool:
    """Keys the path notation can address unambiguously."""

    if isinstance(document, dict):
        return all(
            not any(ch in key for ch in ".[]") and _simple_keys(value)
            for key, value in document.items()
        )
    if isinstance(document, list):
        return all(_simple_keys(item) for item in document)
    return True


# -------------------------------------------------------------------------
# The exact comparison
# -------------------------------------------------------------------------
@settings(max_examples=100, deadline=None)
@given(_DOCUMENTS)
def test_property_a_document_equals_itself_leaf_by_leaf(document):
    normalized = common.json_normalized(document)
    check = common.compare_exact("self", document, copy.deepcopy(document))
    assert check.identical
    assert check.differences == ()
    assert check.n_leaves == len(_leaf_paths(normalized))


@settings(max_examples=150, deadline=None)
@given(_DOCUMENTS, st.data())
def test_property_any_one_moved_leaf_is_found_at_its_path(document, data):
    document = common.json_normalized(document)
    if not _simple_keys(document):
        return
    leaves = _leaf_paths(document)
    if not leaves:
        return
    path, value = data.draw(st.sampled_from(leaves))
    moved = _set(document, path, _moved(value))
    check = common.compare_exact("moved", document, moved)
    assert check.differences == (path,)
    with pytest.raises(common.ReproductionMismatchError) as error:
        common.require_identical([check], stage="test")
    message = str(error.value)
    assert repr(path) in message
    assert "nothing is written" in message
    shown = (repr(value), repr(_moved(value)))
    if isinstance(value, float) and not any(text in path for text in shown):
        # Paths only: the refusal never prints the committed value.
        assert not any(text in message for text in shown)


def test_floats_compare_bit_for_bit():
    assert not common.compare_exact("z", 0.0, -0.0).identical
    nudged = math.nextafter(0.1 + 0.2, math.inf)
    assert not common.compare_exact("u", 0.1 + 0.2, nudged).identical
    assert common.compare_exact(
        "same", 0.30000000000000004, 0.1 + 0.2
    ).identical


@pytest.mark.parametrize(
    ("committed", "recomputed", "expected"),
    [
        (1, 1.0, ["$"]),
        (True, 1, ["$"]),
        (None, 0, ["$"]),
        ({"a": 1}, {"a": 1, "b": 2}, ["$.b (present on one side only)"]),
        ({"a": [1, 2]}, {"a": [1]}, ["$.a (lengths differ)"]),
        ({"a": {"b": 1}}, {"a": 1}, ["$.a (structure differs)"]),
        ({"a": [1, 2.5]}, {"a": [1, 2.5]}, []),
    ],
)
def test_type_key_and_length_differences(committed, recomputed, expected):
    check = common.compare_exact("x", committed, recomputed)
    assert list(check.differences) == expected


def test_comparison_goes_through_the_runners_json_encoding():
    """Tuples and lists encode alike, so they compare equal; NaN refuses."""

    assert common.compare_exact("t", {"a": (1, 2)}, {"a": [1, 2]}).identical
    with pytest.raises(ValueError):
        common.compare_exact("nan", float("nan"), float("nan"))


def test_require_identical_passes_identical_checks():
    common.require_identical(
        [common.compare_exact("a", {"x": 1.5}, {"x": 1.5})], stage="test"
    )


def test_check_record_caps_paths():
    check = common.ReproductionCheck(
        "many", 10, tuple(f"$[{i}]" for i in range(80))
    )
    record = check.as_dict()
    assert record["n_differences"] == 80
    assert len(record["differing_paths"]) == 50
    assert record["identical"] is False


def test_exact_comparison_declares_no_tolerance():
    assert common.EXACT_COMPARISON["tolerance"] is None


# -------------------------------------------------------------------------
# Labels
# -------------------------------------------------------------------------
def test_the_invented_headers_agree():
    assert common.INVENTED_DATA_HEADER == DRY_RUN_HEADER == INVENTED_HEADER


def test_post_hoc_labels():
    assert common.POST_HOC_LABELS == (
        "registered, one-shot, post hoc, not blind",
        "report-only",
    )


# -------------------------------------------------------------------------
# Files
# -------------------------------------------------------------------------
def test_write_new_never_overwrites(tmp_path):
    path = tmp_path / "artifact.json"
    common.write_new(path, "one")
    with pytest.raises(FileExistsError):
        common.write_new(path, "two")
    assert path.read_text() == "one"


def _artifact(tmp_path, document=None, sidecar=None):
    path = tmp_path / "parent_v1.json"
    path.write_text(json.dumps(document or {"cells": [1.5]}))
    digest = common.file_sha256(path)
    record = {"artifact": path.name, "artifact_sha256": digest}
    if sidecar is not None:
        record.update(sidecar)
    path.with_suffix(".env.json").write_text(json.dumps(record))
    return path, digest


def test_a_committed_artifact_loads_with_its_pin_and_sidecar(tmp_path):
    path, digest = _artifact(tmp_path)
    parent = common.load_committed_artifact(path, expected_sha256=digest)
    assert parent.document == {"cells": [1.5]}
    assert parent.sha256 == digest
    assert parent.record(tmp_path)["path"] == path.name
    assert parent.record()["sidecar_artifact_sha256"] == digest


def test_other_bytes_are_refused(tmp_path):
    path, _ = _artifact(tmp_path)
    with pytest.raises(ValueError, match="not the committed"):
        common.load_committed_artifact(path, expected_sha256="0" * 64)


@pytest.mark.parametrize(
    ("sidecar", "match"),
    [
        ({"artifact": "another.json"}, "does not name"),
        ({"artifact_sha256": "0" * 64}, "does not bind"),
    ],
)
def test_an_unbound_sidecar_is_refused(tmp_path, sidecar, match):
    path, digest = _artifact(tmp_path, sidecar=sidecar)
    with pytest.raises(ValueError, match=match):
        common.load_committed_artifact(path, expected_sha256=digest)


def test_an_invented_parent_records_no_path():
    record = common.CommittedArtifact(document={"x": 1}).record()
    assert record["path"] is None
    assert record["sha256"] is None


# -------------------------------------------------------------------------
# The cohort side frame (G1) on G3's codes
# -------------------------------------------------------------------------
_RACE = {d.key: d for d in g3.MINT8_SCHEME.dimensions}["race_ethnicity"]
_COUNTRY = {d.key: d for d in g3.MINT8_SCHEME.dimensions}["country_of_birth"]
_EDUCATION = {d.key: d for d in g3.MINT8_SCHEME.dimensions}["education"]


def _side(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "race_ethnicity_mint8",
            "race_ethnicity_mint8_status",
            "race_ethnicity_status",
        ],
    )


def test_side_frame_labels_become_g3_codes():
    frame = _side(
        [
            ("White, non-Hispanic", g1.ASSIGNED, g1.KNOWN),
            ("Hispanic or Latino, any race", g1.ASSIGNED, g1.KNOWN),
            (pd.NA, g1.ATTRIBUTE_UNKNOWN, g1.NEVER_HEAD_OR_SPOUSE),
            (pd.NA, "unresolved:multiple_races", g1.KNOWN),
        ]
    )
    codes = common.side_frame_codes(frame, _RACE)
    assert codes.codes == (
        "white_non_hispanic",
        "hispanic_any_race",
        "attribute_unknown:never_head_or_spouse",
        "unresolved:multiple_races",
    )
    assert codes.unclassified_codes == (
        "attribute_unknown:never_head_or_spouse",
        "unresolved:multiple_races",
    )


@pytest.mark.parametrize(
    ("row", "match"),
    [
        (("Martian", g1.ASSIGNED, g1.KNOWN), "is not one of"),
        (("White, non-Hispanic", g1.ATTRIBUTE_UNKNOWN, g1.KNOWN), "carries"),
        ((pd.NA, "guessed", g1.KNOWN), "undocumented"),
    ],
)
def test_side_frame_codes_refuse_what_g1_does_not_say(row, match):
    with pytest.raises(ValueError, match=match):
        common.side_frame_codes(_side([row]), _RACE)


def test_only_side_frame_dimensions_map():
    with pytest.raises(ValueError, match="not a side-frame dimension"):
        common.side_frame_codes(_side([]), _EDUCATION)


def test_every_g1_mint8_label_is_a_g3_label():
    """G1's scheme file and G3's MINT8 scheme print the same labels."""

    schemes = g1.load_schemes()["schemes"]["mint8"]["dimensions"]
    for key, dimension in (
        ("race_ethnicity", _RACE),
        ("country_of_birth", _COUNTRY),
    ):
        g3_labels = {category.label for category in dimension.categories}
        assert set(schemes[key]["categories"].values()) <= g3_labels


#: G1's years-of-schooling domain: 0 ("completed no grades", from the
#: family-file recode) through the individual file's top code.
_YEARS_DOMAIN = (0, gap.EDUCATION_YEARS_RANGE[1])
_YEARS = st.integers(min_value=_YEARS_DOMAIN[0], max_value=_YEARS_DOMAIN[1])


@settings(max_examples=60, deadline=None)
@given(st.lists(_YEARS, max_size=40))
def test_property_g1_and_g3_place_every_years_value_alike(years):
    """Differential: G1's MINT8 education label and G3's band agree on
    every value of G1's documented domain."""

    spec = g1.load_schemes()["schemes"]["mint8"]["dimensions"]["education"]
    frame = pd.DataFrame(
        {"education_years": pd.array(years + [pd.NA], dtype="Int64")}
    )
    labels, status = g1.apply_category_scheme(frame, "education", spec)
    frame["education_mint8"] = labels
    record = common.education_agreement(frame, _EDUCATION)
    assert record["n_with_years"] == len(years)
    assert (status.iloc[:-1] == g1.ASSIGNED).all()


def test_g1_and_g3_agree_on_the_whole_domain():
    low, high = _YEARS_DOMAIN
    spec = g1.load_schemes()["schemes"]["mint8"]["dimensions"]["education"]
    frame = pd.DataFrame(
        {
            "education_years": pd.array(
                list(range(low, high + 1)), dtype="Int64"
            )
        }
    )
    frame["education_mint8"], _ = g1.apply_category_scheme(
        frame, "education", spec
    )
    record = common.education_agreement(frame, _EDUCATION)
    assert record["n_with_years"] == high - low + 1


def test_g1_refuses_years_outside_its_domain():
    spec = g1.load_schemes()["schemes"]["mint8"]["dimensions"]["education"]
    frame = pd.DataFrame(
        {"education_years": pd.array([_YEARS_DOMAIN[1] + 1], dtype="Int64")}
    )
    with pytest.raises(ValueError, match="undocumented"):
        g1.apply_category_scheme(frame, "education", spec)


def test_an_education_disagreement_is_refused():
    frame = pd.DataFrame(
        {
            "education_years": pd.array([12], dtype="Int64"),
            "education_mint8": ["Bachelor"],
        }
    )
    with pytest.raises(ValueError, match="differently"):
        common.education_agreement(frame, _EDUCATION)


def test_marital_codes_declare_only_present_non_mint_statuses():
    codes = common.marital_codes(
        ["married", "unknown", "widowed"],
        unclassified=("unknown", "no_marriage_history"),
    )
    assert codes.codes == ("married", "unknown", "widowed")
    assert codes.unclassified_codes == ("unknown",)
    with pytest.raises(ValueError, match="cannot be declared"):
        common.marital_codes(["married"], unclassified=("married",))


@given(
    st.lists(st.integers(min_value=1880, max_value=2030), max_size=20),
    st.integers(min_value=1950, max_value=2100),
)
def test_property_age_in_year(births, year):
    ages = common.age_in_year(births, year)
    assert [age + birth for age, birth in zip(ages, births, strict=True)] == [
        year
    ] * len(births)


def test_age_refuses_booleans():
    with pytest.raises(ValueError, match="integers"):
        common.age_in_year([True], 2022)
    with pytest.raises(ValueError, match="integers"):
        common.age_in_year([np.bool_(False)], 2022)


# -------------------------------------------------------------------------
# INVENTED side-frame inputs
# -------------------------------------------------------------------------
def _invented_persons(n: int = 30) -> pd.DataFrame:
    roles = ["head", "spouse", None]
    return pd.DataFrame(
        {
            "person_id": [1001 + i for i in range(n)],
            "role": pd.array([roles[i % 3] for i in range(n)], dtype="string"),
        }
    )


def test_invented_inputs_pass_g1s_real_builder():
    persons = _invented_persons()
    inputs = common.invented_group_attribute_inputs(persons, wave=2023)
    assert inputs.provenance["kind"] == "INVENTED"
    assert inputs.provenance["label"] == common.INVENTED_DATA_HEADER
    built = g1.build_group_attributes(
        inputs, persons["person_id"].tolist(), anchor_waves=(2023,)
    )
    assert built.frame["person_id"].tolist() == sorted(persons["person_id"])
    # The PSID asks race and birthplace of heads and spouses only.
    others = built.frame.set_index("person_id").loc[
        persons.loc[persons["role"].isna(), "person_id"]
    ]
    assert (others["race_ethnicity_status"] == g1.NEVER_HEAD_OR_SPOUSE).all()
    record = common.education_agreement(built.frame, _EDUCATION)
    assert record["g3_band_equals_g1_label"] is True


def test_invented_inputs_are_deterministic():
    persons = _invented_persons()
    first = common.invented_group_attribute_inputs(persons, wave=2023, seed=5)
    second = common.invented_group_attribute_inputs(persons, wave=2023, seed=5)
    pd.testing.assert_frame_equal(first.reports, second.reports)
    pd.testing.assert_frame_equal(first.education, second.education)


def test_invented_inputs_refuse_a_wave_without_birthplace():
    with pytest.raises(ValueError, match="2013-2023"):
        common.invented_group_attribute_inputs(_invented_persons(), wave=1999)


def test_invented_inputs_refuse_an_undocumented_role():
    persons = _invented_persons(3)
    persons["role"] = pd.array(["head", "boarder", None], dtype="string")
    with pytest.raises(ValueError, match="undocumented role"):
        common.invented_group_attribute_inputs(persons, wave=2023)
