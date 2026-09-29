"""U2 parameters (section 13, group "Parameters").

Complete years, 2022 precision, exact 2012 threshold/SSI overlap, unknown
revision refusal and constant checks; U1 captures refused as U2 sources;
caller-supplied hashes cannot bypass the target-bound bundle; U1's own
guards refuse the Track M and U2 captures.
"""

from __future__ import annotations

import copy
import dataclasses
import inspect
import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.min_benefit_track_m import thresholds as track_m
from populace_dynamics.uniform_cut_track_u import runner as u1_runner
from populace_dynamics.uniform_cut_track_u2 import (
    diagnostics,
    identity,
    invented,
    parameters,
)

ROOT = Path(__file__).resolve().parents[2]
U2_SSI = ROOT / "data" / "external" / "track_u2_ssi_parameters_2012_2022.json"
TRACK_M = (
    ROOT / "data" / "external" / "census_poverty_thresholds_1982_2022.json"
)


@pytest.fixture(scope="module")
def thresholds():
    return parameters.load_u2_thresholds()


@pytest.fixture(scope="module")
def ssi():
    return parameters.load_u2_ssi_parameters()


def test_threshold_capture_is_the_pinned_track_m_file(thresholds):
    assert parameters.THRESHOLDS_PATH == TRACK_M
    assert parameters.THRESHOLDS_SHA256 == track_m.TRACK_M_THRESHOLDS_SHA256
    assert thresholds.provenance["target_id"] == "U2"
    assert thresholds.provenance["sha256"] == parameters.THRESHOLDS_SHA256


def test_threshold_coverage_includes_every_required_year(thresholds):
    for year in (2012, 2014, 2016, 2018, 2020, 2022):
        assert year in thresholds.weighted_average
        assert year in thresholds.matrix
        for size in range(1, 12):
            value, _ = ap.threshold_for(
                thresholds, year, size, 0, "census_weighted_average_65plus"
            )
            assert value > 0


def test_2012_equals_u1_capture_in_every_entry(thresholds):
    u1 = ap.load_poverty_thresholds()
    assert thresholds.weighted_average[2012] == u1.weighted_average[2012]
    assert thresholds.matrix[2012] == u1.matrix[2012]


def test_2022_precision_is_read_as_captured(thresholds):
    raw = json.loads(TRACK_M.read_text())
    assert thresholds.provenance["weighted_average_unit_dollars_2022"] == 10
    for row, value in raw["weighted_average"]["2022"].items():
        assert thresholds.weighted_average[2022][row] == float(value)


def test_ssi_capture_years_revision_constants_and_2012(ssi):
    assert sorted(ssi.fbr_individual_monthly) == list(range(2012, 2023))
    assert sorted(ssi.fbr_couple_monthly) == list(range(2012, 2023))
    assert ssi.provenance["target_id"] == "U2"
    u1 = ap.load_ssi_parameters()
    assert ssi.fbr_individual_monthly[2012] == u1.fbr_individual_monthly[2012]
    assert ssi.fbr_couple_monthly[2012] == u1.fbr_couple_monthly[2012]
    for name in (
        "general_income_exclusion_monthly",
        "earned_income_exclusion_monthly",
        "earned_income_share_excluded",
        "resource_limit_individual",
        "resource_limit_couple",
    ):
        assert getattr(ssi, name) == getattr(u1, name)


@pytest.mark.parametrize("revision", [None, "", "unknown", "abc123"])
def test_unknown_revision_is_refused(revision):
    data = json.loads(U2_SSI.read_text())
    data["source"]["policyengine_us_revision"] = revision
    with pytest.raises(parameters.U2ParameterError, match="revision"):
        parameters.validate_u2_ssi_document(data)


def test_varying_constants_and_other_years_are_refused():
    data = json.loads(U2_SSI.read_text())
    varying = copy.deepcopy(data)
    varying["verification"]["constant_parameters"][
        "general_income_exclusion"
    ] = list(range(2012, 2020))
    with pytest.raises(parameters.U2ParameterError, match="not constant"):
        parameters.validate_u2_ssi_document(varying)
    short = copy.deepcopy(data)
    short["years"] = list(range(2013, 2023))
    with pytest.raises(parameters.U2ParameterError, match="2012-2022"):
        parameters.validate_u2_ssi_document(short)
    shifted = copy.deepcopy(data)
    shifted["federal_benefit_rate_monthly"]["individual"]["2012"] = 699.0
    with pytest.raises(parameters.U2ParameterError, match="2012"):
        parameters.validate_u2_ssi_document(shifted)
    other = copy.deepcopy(data)
    other["target_id"] = "U1"
    with pytest.raises(ValueError, match="not 'U2'"):
        parameters.validate_u2_ssi_document(other)


def test_loaders_take_no_caller_supplied_hash():
    for loader in (
        parameters.load_u2_thresholds,
        parameters.load_u2_ssi_parameters,
    ):
        assert list(inspect.signature(loader).parameters) == []


def test_u1_captures_are_refused_as_u2_sources(u2_params):
    u1_thresholds = parameters.U2Parameters(
        thresholds=ap.load_poverty_thresholds(),
        ssi=u2_params.ssi,
        life_tables=u2_params.life_tables,
    )
    with pytest.raises(parameters.U2ParameterError, match="U1 capture"):
        parameters.check_u2_parameters(u1_thresholds, ap.INVENTED)
    u1_ssi = parameters.U2Parameters(
        thresholds=u2_params.thresholds,
        ssi=ap.load_ssi_parameters(),
        life_tables=u2_params.life_tables,
    )
    with pytest.raises(parameters.U2ParameterError, match="U1 capture"):
        parameters.check_u2_parameters(u1_ssi, ap.INVENTED)
    with pytest.raises(parameters.U2ParameterError, match="U1 capture"):
        parameters._read_pinned(
            parameters.U1_THRESHOLDS_PATH, parameters.THRESHOLDS_SHA256, "x"
        )


def test_registered_check_needs_every_u2_pin(u2_params, thresholds):
    with pytest.raises(parameters.U2ParameterError, match="Census"):
        parameters.check_u2_parameters(u2_params, ap.REGISTERED_REAL)
    committed = dataclasses.replace(u2_params, thresholds=thresholds)
    parameters.check_u2_parameters(committed, ap.REGISTERED_REAL)
    relabelled = dataclasses.replace(
        committed,
        thresholds=dataclasses.replace(
            thresholds,
            provenance={**thresholds.provenance, "sha256": "0" * 64},
        ),
    )
    with pytest.raises(parameters.U2ParameterError, match="Census"):
        parameters.check_u2_parameters(relabelled, ap.REGISTERED_REAL)
    ssi_hash = dataclasses.replace(
        committed,
        ssi=dataclasses.replace(
            committed.ssi,
            provenance={**committed.ssi.provenance, "sha256": "0" * 64},
        ),
    )
    with pytest.raises(parameters.U2ParameterError, match="SSI"):
        parameters.check_u2_parameters(ssi_hash, ap.REGISTERED_REAL)


def test_u1_runner_refuses_the_track_m_and_u2_captures(thresholds, ssi):
    params = u1_runner.committed_parameters(ap.load_poverty_thresholds())
    track_m_thresholds = dataclasses.replace(
        params,
        thresholds=dataclasses.replace(
            thresholds,
            provenance={
                "kind": "census_capture",
                "sha256": parameters.THRESHOLDS_SHA256,
            },
        ),
    )
    with pytest.raises(u1_runner.TrackURunError, match="Census"):
        u1_runner._check_parameters(track_m_thresholds, ap.REGISTERED_REAL)
    u2_ssi = dataclasses.replace(params, ssi=ssi)
    with pytest.raises(u1_runner.TrackURunError, match="SSI"):
        u1_runner._check_parameters(u2_ssi, ap.REGISTERED_REAL)
    with pytest.raises(ap.AdjustedPovertyError, match="sha256"):
        ap.load_poverty_thresholds(TRACK_M)
    with pytest.raises(ap.AdjustedPovertyError, match="sha256"):
        ap.load_ssi_parameters(U2_SSI)


def test_diagnostics_pin_equals_the_parameter_pin():
    assert diagnostics.SSI_SHA256 == parameters.SSI_SHA256
    assert diagnostics.SSI_PATH == parameters.SSI_PATH
    rates = diagnostics.federal_benefit_rates()
    assert (
        rates["individual"]
        == parameters.load_u2_ssi_parameters().fbr_individual_monthly
    )


def test_invented_fbr_placement_table_equals_the_capture():
    ssi = parameters.load_u2_ssi_parameters()
    assert {
        year: float(value)
        for year, value in invented.FBR_INDIVIDUAL_MONTHLY.items()
    } == dict(ssi.fbr_individual_monthly)


def test_life_tables_are_the_inherited_pins(u2_params):
    for basis, table in u2_params.life_tables.items():
        assert table.name == basis
    assert (
        u2_params.life_tables["nchs_2000"].source["sha256"]
        == ap.NCHS_2000_SHA256
    )
    assert identity.U1_SSI_SHA256 == ap.SSI_PARAMETERS_SHA256
    assert identity.U1_THRESHOLDS_SHA256 == ap.THRESHOLDS_SHA256


def test_invented_life_table_only_in_an_invented_run(u2_params):
    fake = ap.LifeTable(
        name=ap.INVENTED_LIFE_TABLE,
        qx={"male": (0.5,) * 120, "female": (0.5,) * 120},
    )
    bundle = dataclasses.replace(
        u2_params, life_tables={**u2_params.life_tables, "nchs_2000": fake}
    )
    parameters.check_u2_parameters(bundle, ap.INVENTED)
    with pytest.raises(parameters.U2ParameterError):
        parameters.check_u2_parameters(bundle, ap.REGISTERED_REAL)


# ---------------------------------------------------------------------------
# Review round 1, finding 3: the registered check verifies content, not the
# provenance label.  Every altered value below is INVENTED.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def pinned():
    """U2's registered bundle, read from the pinned files."""

    return parameters.committed_u2_parameters()


def _nested_copy(mapping):
    return {
        key: (_nested_copy(value) if isinstance(value, dict) else value)
        for key, value in mapping.items()
    }


def _alter(params, component: str, location: tuple, value: float):
    """``params`` with one value replaced and every provenance kept."""

    if component in ("weighted_average", "matrix"):
        table = _nested_copy(getattr(params.thresholds, component))
        node = table
        for key in location[:-1]:
            node = node[key]
        node[location[-1]] = value
        return dataclasses.replace(
            params,
            thresholds=dataclasses.replace(
                params.thresholds, **{component: table}
            ),
        )
    if component in ("fbr_individual_monthly", "fbr_couple_monthly"):
        schedule = dict(getattr(params.ssi, component))
        schedule[location[0]] = value
        return dataclasses.replace(
            params,
            ssi=dataclasses.replace(params.ssi, **{component: schedule}),
        )
    if component == "ssi_constant":
        return dataclasses.replace(
            params,
            ssi=dataclasses.replace(params.ssi, **{location[0]: value}),
        )
    assert component == "qx", component
    basis, sex, age = location
    table = params.life_tables[basis]
    qx = {key: tuple(values) for key, values in table.qx.items()}
    qx[sex] = qx[sex][:age] + (value,) + qx[sex][age + 1 :]
    return dataclasses.replace(
        params,
        life_tables={
            **params.life_tables,
            basis: dataclasses.replace(table, qx=qx),
        },
    )


def test_the_pinned_bundle_passes_and_labels_are_unchanged(pinned):
    parameters.check_u2_parameters(pinned, ap.REGISTERED_REAL)
    assert pinned.thresholds.provenance["sha256"] == (
        parameters.THRESHOLDS_SHA256
    )


@pytest.mark.parametrize(
    "component, location",
    [
        # The round-1 review's case: one weighted average set to an
        # INVENTED 1.0 under the pinned Track M provenance.
        ("weighted_average", (2014, "one_65_plus")),
        ("weighted_average", (2012, "two_65_plus")),
        ("matrix", (2022, "one_65_plus", 0)),
        ("fbr_individual_monthly", (2016,)),
        ("fbr_couple_monthly", (2012,)),
        ("ssi_constant", ("general_income_exclusion_monthly",)),
        ("ssi_constant", ("resource_limit_couple",)),
        ("qx", ("nchs_2000", "female", 67)),
        ("qx", ("ssa_period_2004", "male", 80)),
    ],
)
def test_an_altered_value_under_the_pinned_label_refuses(
    pinned, component, location
):
    altered = _alter(pinned, component, location, 1.0)
    assert parameters.parameters_content_sha256(altered) != (
        parameters.parameters_content_sha256(pinned)
    )
    # The label still names the pinned captures ...
    assert altered.thresholds.provenance == pinned.thresholds.provenance
    assert altered.ssi.provenance == pinned.ssi.provenance
    # ... and the invented run's checks still accept it (labels only) ...
    parameters.check_u2_parameters(altered, ap.INVENTED)
    # ... but the registered check reads the content.
    with pytest.raises(parameters.U2ParameterError, match="provenance label"):
        parameters.check_u2_parameters(altered, ap.REGISTERED_REAL)


def test_an_in_place_edit_after_loading_refuses(pinned):
    """The frozen dataclasses hold plain dicts: an in-place edit of a
    loaded bundle is caught because the check rehashes the content."""

    bundle = copy.deepcopy(pinned)
    parameters.check_u2_parameters(bundle, ap.REGISTERED_REAL)
    bundle.thresholds.weighted_average[2020]["one_65_plus"] += 1.0
    with pytest.raises(parameters.U2ParameterError, match="thresholds"):
        parameters.check_u2_parameters(bundle, ap.REGISTERED_REAL)


def test_an_extra_threshold_year_refuses(pinned):
    extra = _nested_copy(pinned.thresholds.weighted_average)
    extra[2030] = dict(extra[2022])
    bundle = dataclasses.replace(
        pinned,
        thresholds=dataclasses.replace(
            pinned.thresholds, weighted_average=extra
        ),
    )
    with pytest.raises(parameters.U2ParameterError, match="thresholds"):
        parameters.check_u2_parameters(bundle, ap.REGISTERED_REAL)


def test_the_content_digest_reads_numbers_not_labels_or_order(pinned):
    digest = parameters.parameters_content_sha256(pinned)
    relabelled = dataclasses.replace(
        pinned,
        thresholds=dataclasses.replace(
            pinned.thresholds, provenance={"kind": "anything"}
        ),
    )
    assert parameters.parameters_content_sha256(relabelled) == digest
    reordered = dataclasses.replace(
        pinned,
        thresholds=dataclasses.replace(
            pinned.thresholds,
            weighted_average=dict(
                reversed(list(pinned.thresholds.weighted_average.items()))
            ),
        ),
    )
    assert parameters.parameters_content_sha256(reordered) == digest
    whole = {
        year: {
            row: int(v) if float(v).is_integer() else v for row, v in r.items()
        }
        for year, r in pinned.thresholds.weighted_average.items()
    }
    as_int = dataclasses.replace(
        pinned,
        thresholds=dataclasses.replace(
            pinned.thresholds, weighted_average=whole
        ),
    )
    assert parameters.parameters_content_sha256(as_int) == digest


def _locations(pinned):
    """Every value location the registered check covers."""

    out = []
    for year, rows in pinned.thresholds.weighted_average.items():
        out += [("weighted_average", (year, row)) for row in rows]
    for year, rows in pinned.thresholds.matrix.items():
        for row, cells in rows.items():
            out += [("matrix", (year, row, cell)) for cell in cells]
    for name in ("fbr_individual_monthly", "fbr_couple_monthly"):
        out += [(name, (year,)) for year in getattr(pinned.ssi, name)]
    out += [
        ("ssi_constant", (name,))
        for name in (
            "general_income_exclusion_monthly",
            "earned_income_exclusion_monthly",
            "earned_income_share_excluded",
            "resource_limit_individual",
            "resource_limit_couple",
        )
    ]
    for basis, table in pinned.life_tables.items():
        for sex, values in table.qx.items():
            out += [("qx", (basis, sex, age)) for age in range(len(values))]
    return out


def _current(pinned, component, location):
    if component in ("weighted_average", "matrix"):
        node = getattr(pinned.thresholds, component)
        for key in location:
            node = node[key]
        return float(node)
    if component in ("fbr_individual_monthly", "fbr_couple_monthly"):
        return float(getattr(pinned.ssi, component)[location[0]])
    if component == "ssi_constant":
        return float(getattr(pinned.ssi, location[0]))
    basis, sex, age = location
    return float(pinned.life_tables[basis].qx[sex][age])


_PINNED = parameters.committed_u2_parameters()
_LOCATIONS = _locations(_PINNED)


@settings(max_examples=150, deadline=None)
@given(
    where=st.sampled_from(_LOCATIONS),
    value=st.floats(
        min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False
    )
    | st.floats(
        min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False
    ),
)
def test_any_single_altered_value_refuses_the_registered_check(where, value):
    """Invariant: the registered check accepts a bundle whose provenance
    names the pinned captures iff every value equals the pinned files'.
    One value moved anywhere (threshold, SSI or life-table ``qx``) under
    the unchanged labels refuses."""

    component, location = where
    if component == "qx":
        value = min(value, 1.0)
    old = _current(_PINNED, component, location)
    altered = _alter(_PINNED, component, location, value)
    if value == old:
        parameters.check_u2_parameters(altered, ap.REGISTERED_REAL)
        return
    with pytest.raises(parameters.U2ParameterError, match="provenance label"):
        parameters.check_u2_parameters(altered, ap.REGISTERED_REAL)
