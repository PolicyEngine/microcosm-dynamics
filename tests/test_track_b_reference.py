"""Invented historical-archive encoding and authentication checks."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import runner
from populace_dynamics.track_b.equality import compare_frames
from populace_dynamics.track_b.runner import (
    BASELINE_SHA256,
    frame_payload,
    json_bytes,
    read_historical_reference,
    sha256,
)


def archive(frame):
    return {
        "schema_version": "track_b_b1_historical_reference.v1",
        "baseline_sha256": BASELINE_SHA256,
        "origin": "historical_candidate3_run",
        "records": [
            {
                "seed": 0,
                "draw": 0,
                "scored": frame_payload(frame),
                "fit_signature": {"sha256": "invented-fit"},
                "rng_signature": {"n_periods": 8},
            }
        ],
    }


def frame(earnings):
    return pd.DataFrame(
        {
            "person_id": [1],
            "period": [2016],
            "earnings": np.array([earnings], dtype=np.float64),
            "weight": [2.0],
            "cohort": ["prime"],
        }
    )


def read_committed(path, committed):
    """Records read with ``committed`` standing in for the committed hash."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(runner, "HISTORICAL_REFERENCE_SHA256", committed)
        return runner.authenticated_records(read_historical_reference(path))


@settings(max_examples=30, deadline=None)
@given(value=st.floats(width=64, allow_infinity=False, allow_nan=False))
def test_archive_preserves_float_bits(tmp_path_factory, value):
    directory = tmp_path_factory.mktemp("reference")
    expected = frame(value)
    raw = json_bytes(archive(expected))
    path = directory / "invented.json"
    path.write_bytes(raw)
    observed = read_committed(path, sha256(raw))
    assert compare_frames(expected, observed[0, 0]["scored"])["equal"]


@pytest.mark.parametrize(
    "mutation", ["sha256", "origin", "baseline", "duplicate"]
)
def test_archive_rejects_wrong_identity(tmp_path, mutation):
    content = archive(frame(-0.0))
    if mutation == "origin":
        content["origin"] = "regenerated_today"
    elif mutation == "baseline":
        content["baseline_sha256"] = "wrong-baseline"
    elif mutation == "duplicate":
        content["records"] *= 2
    raw = json_bytes(content)
    path = tmp_path / "invented.json"
    path.write_bytes(raw)
    digest = "wrong-hash" if mutation == "sha256" else sha256(raw)
    with pytest.raises(ValueError):
        read_committed(path, digest)


def test_archive_preserves_missing_values_and_signed_zero(tmp_path):
    expected = frame(-0.0)
    expected["nullable"] = pd.Series([pd.NA], dtype="Int64")
    raw = json_bytes(archive(expected))
    path = tmp_path / "invented.json"
    path.write_bytes(raw)
    actual = read_committed(path, sha256(raw))[0, 0]["scored"]
    assert compare_frames(expected, actual)["equal"]
    assert np.signbit(actual["earnings"].iloc[0])
