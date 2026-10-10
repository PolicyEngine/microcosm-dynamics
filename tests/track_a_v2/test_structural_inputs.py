"""Invented preparation differential with forbidden diagnostics poisoned."""

import pandas as pd
import pytest

from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import benefits as legacy_benefits
from populace_dynamics.cola_track_a import invented, opening
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.ss import benefits, statutory_aime
from populace_dynamics.track_a_v2.structural_inputs import (
    prepare_structural_cohort,
)


def test_structural_preparation_matches_inputs_without_weight_sums_or_benefits(
    monkeypatch,
):
    """Omitting diagnostics preserves every projection/record input exactly."""
    config = TrackAConfig(rows=tuple(f"R{i}" for i in range(6)))
    raw = invented.invented_psid2010_inputs(seed=7)
    reference = opening.prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(raw),
        data_provenance="invented",
        config=config,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("benefit or weighted diagnostic forbidden")

    original_sum = pd.Series.sum

    def no_weight_sum(series, *args, **kwargs):
        if series.name == "weight":
            forbidden()
        return original_sum(series, *args, **kwargs)

    monkeypatch.setattr(pd.Series, "sum", no_weight_sum)
    monkeypatch.setattr(psid2010, "_diagnostics", forbidden)
    monkeypatch.setattr(psid2010, "_weighted", forbidden)
    monkeypatch.setattr(psid2010, "build_psid2010_cohort", forbidden)
    monkeypatch.setattr(opening, "prepare_track_a_cohort", forbidden)
    monkeypatch.setattr(legacy_benefits, "approximate_pia", forbidden)
    monkeypatch.setattr(legacy_benefits._Calculator, "_level", forbidden)
    monkeypatch.setattr(benefits, "pia", forbidden)
    monkeypatch.setattr(statutory_aime, "aime", forbidden)
    candidate = prepare_structural_cohort(
        raw, data_provenance="invented", config=config
    )
    pd.testing.assert_frame_equal(candidate.persons, reference.persons)
    pd.testing.assert_frame_equal(
        candidate.initial_slice, reference.initial_slice
    )
    assert candidate.careers == reference.careers
    assert candidate.opening == reference.opening
    assert candidate.roster_ids == reference.roster_ids
    assert candidate.labels == reference.labels
    assert candidate.diagnostics == {}
    assert (
        candidate.source_provenance["content_sha256"]
        == reference.source_provenance["content_sha256"]
    )


def test_structural_preparation_refuses_invented_source_as_real():
    """Count-only preparation retains the source-provenance boundary."""
    raw = invented.invented_psid2010_inputs(seed=7)
    with pytest.raises(ValueError, match="provenance contradicts"):
        prepare_structural_cohort(raw, data_provenance="registered_real")
