"""Staged-PSID side-frame coverage for the four blind-test populations.

Skipped without the products under ``~/PolicyEngine/psid-data``. The
official cohort readers and selectors determine the population; these
tests run no projection, benefit rule, poverty measure or tabulation.
Only identifiers, labels, documented code domains, source seals and
attribute availability are checked. No group distribution is computed
or pinned. Bulky cohort inputs are released between populations.
"""

from __future__ import annotations

import gc
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from populace_dynamics.cohorts import age67, group_attributes, psid2010
from populace_dynamics.data import family, family_income
from populace_dynamics.data import group_attributes_psid as gap
from populace_dynamics.min_benefit_track_m import cohort as track_m
from populace_dynamics.min_benefit_track_m import structure

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()
_CODEBOOKS = gap.load_codebook_values()["family"]
_NEEDED = (
    REAL_DATA / "ind2023er" / "IND2023ER.txt",
    REAL_DATA / "ind2023er" / "IND2023ER.sps",
    REAL_DATA / "ind2023er" / "IND2023ER_formats.sas",
    REAL_DATA / "mh85_23" / "MH85_23.txt",
    REAL_DATA / "mh85_23" / "MH85_23.sps",
    *(
        REAL_DATA / "family" / str(wave)
        for wave in set(family.FAMILY_WAVES) | set(gap.RACE_WAVES)
    ),
    *(
        REAL_DATA / _CODEBOOKS[str(wave)]["codebook"]["path"]
        for wave in gap.RACE_WAVES
    ),
    *(
        REAL_DATA / "wealth" / str(wave) / name
        for wave, pins in family_income.WEALTH_SUPPLEMENT_SHA256.items()
        for name in pins
    ),
)
needs_real_psid = pytest.mark.skipif(
    not all(path.exists() for path in _NEEDED),
    reason="staged PSID products, family codebooks or wealth absent",
)


@pytest.fixture(scope="module")
def attribute_inputs():
    # This loader verifies every selected .sps label, individual-format
    # domain, family-codebook domain and staged-codebook SHA-256 before
    # returning data. Its audit records the files those checks opened.
    inputs = group_attributes.load_group_attribute_inputs(psid_dir=REAL_DATA)
    provenance = inputs.provenance
    assert provenance["kind"] == "psid_files"
    assert inputs.universe.is_unique
    assert not inputs.reports.duplicated(["person_id", "wave"]).any()
    assert not inputs.education.duplicated(["person_id", "wave"]).any()
    assert provenance["psid_files_sha256"]
    assert all(
        len(digest) == 64
        for digest in provenance["psid_files_sha256"].values()
    )
    assert set(provenance["codebook_pdf_sha256"]) == {
        str(wave) for wave in gap.RACE_WAVES
    }
    assert provenance["input_frames_sha256"] == (
        group_attributes.input_frames_sha256(inputs)
    )
    yield inputs
    del inputs
    gc.collect()


def _assert_coverage(
    inputs: group_attributes.GroupAttributeInputs,
    roster: pd.DataFrame,
    anchor_waves: Iterable[int],
) -> None:
    """Check an identifier-only roster's total join and availability."""

    assert len(roster) > 0
    ids = sorted(set(int(pid) for pid in roster["person_id"]))
    before = group_attributes.input_frames_sha256(inputs)
    built = group_attributes.build_group_attributes(
        inputs, ids, anchor_waves=anchor_waves
    )
    frame = built.frame
    assert len(frame) == len(ids)
    assert frame["person_id"].is_unique
    assert set(frame["person_id"]) == set(ids)
    assert built.provenance["n_persons"] == len(ids)
    assert built.provenance["content_sha256"] == (
        group_attributes.content_sha256(frame)
    )
    assert group_attributes.input_frames_sha256(inputs) == before
    joined = roster.merge(frame, on="person_id", validate="many_to_one")
    assert len(joined) == len(roster)
    pd.testing.assert_series_equal(
        joined["person_id"], roster["person_id"].reset_index(drop=True)
    )

    # Unknown availability is explicit and counted for every attribute.
    # These are status totals, never population counts by group label.
    for column, counts in built.provenance["status_counts"].items():
        assert sum(counts.values()) == len(frame)
        assert frame[column].notna().all()
    for value, status in (
        ("education_years", "education_status"),
        ("country_of_birth", "country_of_birth_status"),
        ("race_ethnicity_mint8", "race_ethnicity_status"),
    ):
        assert (
            frame[value].notna() == frame[status].eq(group_attributes.KNOWN)
        ).all()
    for source in (
        "race_ethnicity_source_wave",
        "education_source_wave",
        "country_of_birth_source_wave",
    ):
        assert frame[source].dropna().isin(gap.RACE_WAVES).all()
    assert (
        frame["education_source_wave"].dropna()
        <= built.provenance["education_cutoff_wave"]
    ).all()


@needs_real_psid
@pytest.mark.parametrize("anchor_wave", (2009, 2011))
def test_projection_cohort_coverage(attribute_inputs, anchor_wave):
    inputs = psid2010.load_psid2010_inputs(
        data_dir=REAL_DATA, anchor_wave=anchor_wave
    )
    built = psid2010.build_psid2010_cohort(
        inputs, psid2010.Psid2010CohortSpec(anchor_wave=anchor_wave)
    )
    roster = built.persons[["person_id"]].copy()
    del built, inputs
    gc.collect()
    _assert_coverage(attribute_inputs, roster, (anchor_wave,))


@needs_real_psid
def test_age67_observation_coverage(attribute_inputs):
    inputs = age67.load_age67_inputs(data_dir=REAL_DATA)
    # U0 is the primary, U1 includes all 1936-45 births, and U0-F is the
    # registered fallback. Repeated observations join the same side row.
    rosters = []
    for row in age67.ROWS:
        built = age67.build_age67_cohort(inputs, age67.Age67Spec(row=row))
        rosters.append(built.observations[["person_id", "wave"]].copy())
        del built
    del inputs
    gc.collect()
    for roster in rosters:
        _assert_coverage(attribute_inputs, roster, age67.WAVES)


@needs_real_psid
def test_track_m_universe_coverage(attribute_inputs):
    inputs = structure.load_structure_inputs(data_dir=REAL_DATA)
    # Reuse the exact official selector (cohort._universe), whose only
    # inputs are these three frames. This does not call build_cohort or
    # load receipt histories, worker records, eligibility or benefits.
    minimal = SimpleNamespace(
        anchor=inputs.anchor,
        earnings=inputs.observed_earnings,
        structure_inputs=SimpleNamespace(
            marriage_history=inputs.marriage_history
        ),
    )
    roster = track_m._universe(minimal)[["person_id"]].copy()
    del minimal, inputs
    gc.collect()
    _assert_coverage(attribute_inputs, roster, (2023,))
