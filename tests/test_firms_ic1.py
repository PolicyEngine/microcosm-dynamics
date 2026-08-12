"""Tests for the IC1 job-spell contract."""

from __future__ import annotations

import pandas as pd
import pytest

from populace_dynamics.firms import ic1


def _ic1(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "person_id": "0000000000000000000001",
        "spell_id": 1,
        "start_period": pd.Period("2023-01", freq="M"),
        "end_period": pd.Period("2023-06", freq="M"),
        "industry": "31",
        "firm_size_band": "B50_99",
        "class_of_worker": "private",
        "earnings_share": 1.0,
        "primary_job": True,
    }
    frame = pd.DataFrame([{**defaults, **row} for row in rows])
    frame["person_id"] = frame["person_id"].astype("string")
    return frame[list(ic1.IC1_COLUMNS)]


def test_valid_frame_passes():
    ic1.validate(_ic1([{}]))


def test_missing_column_rejected():
    with pytest.raises(ValueError, match="missing columns"):
        ic1.validate(_ic1([{}]).drop(columns=["earnings_share"]))


def test_hours_column_rejected_by_name():
    """IC1's hours deferral is explicit; a stray column would read as
    ratified."""
    frame = _ic1([{}])
    frame["hours_band"] = "30-39"
    with pytest.raises(ValueError, match="hours column"):
        ic1.validate(frame)


def test_unregistered_extra_column_rejected():
    frame = _ic1([{}])
    frame["state"] = "OH"
    with pytest.raises(ValueError, match="unregistered columns"):
        ic1.validate(frame)


def test_geography_is_not_an_ic1_column():
    """IC1 deliberately carries no geography; it joins from the person
    table."""
    assert "state" not in ic1.IC1_COLUMNS
    assert not any("geo" in c or "state" in c for c in ic1.IC1_COLUMNS)


def test_numeric_person_id_rejected():
    frame = _ic1([{}])
    frame["person_id"] = [1]
    with pytest.raises(ValueError, match="opaque string"):
        ic1.validate(frame)


def test_spell_id_must_be_unique_within_person():
    frame = _ic1([{"spell_id": 1}, {"spell_id": 1}])
    with pytest.raises(ValueError, match="unique within"):
        ic1.validate(frame)


def test_same_spell_id_across_persons_is_fine():
    ic1.validate(
        _ic1(
            [
                {"person_id": "a", "spell_id": 1},
                {"person_id": "b", "spell_id": 1},
            ]
        )
    )


def test_self_employed_may_not_carry_a_firm_size_band():
    frame = _ic1(
        [{"class_of_worker": "self_employed", "firm_size_band": "LT10"}]
    )
    with pytest.raises(ValueError, match="no defined"):
        ic1.validate(frame)


def test_self_employed_without_a_band_is_valid():
    ic1.validate(
        _ic1([{"class_of_worker": "self_employed", "firm_size_band": None}])
    )


def test_unknown_class_of_worker_rejected():
    with pytest.raises(ValueError, match="class_of_worker"):
        ic1.validate(_ic1([{"class_of_worker": "contractor"}]))


def test_non_canonical_band_rejected():
    with pytest.raises(ValueError, match="canonical IC2 bands"):
        ic1.validate(_ic1([{"firm_size_band": "10-49"}]))


def test_earnings_share_out_of_range_rejected():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        ic1.validate(_ic1([{"earnings_share": 1.4}]))


def test_calibration_universe_keeps_private_only():
    frame = _ic1(
        [
            {"spell_id": 1, "class_of_worker": "private"},
            {"spell_id": 2, "class_of_worker": "federal"},
            {
                "spell_id": 3,
                "class_of_worker": "self_employed",
                "firm_size_band": None,
            },
            {"spell_id": 4, "class_of_worker": "state_local_government"},
        ]
    )
    out = ic1.calibration_universe(frame)
    assert list(out["class_of_worker"]) == ["private"]
    assert out.attrs["excluded_total"] == 3
    assert out.attrs["excluded_from_calibration"]["federal"] == 1


def test_from_sipp_spells_clears_bands_on_self_employed():
    sipp = pd.DataFrame(
        {
            "person_id": ["a", "b"],
            "spell_id": [1, 1],
            "start_month": [
                pd.Period("2023-01", freq="M"),
                pd.Period("2023-02", freq="M"),
            ],
            "end_month": [
                pd.Period("2023-05", freq="M"),
                pd.Period("2023-08", freq="M"),
            ],
            "industry": ["31", "44"],
            "estab_size_band": ["B50_99", "LT10"],
            "class_of_worker": ["private", "self_employed"],
            "earnings_share": [1.0, 1.0],
            "top_earner": [True, True],
        }
    )
    out = ic1.from_sipp_spells(sipp)
    ic1.validate(out)
    assert list(out.columns) == list(ic1.IC1_COLUMNS)
    assert pd.isna(out.loc[1, "firm_size_band"])


def test_from_sipp_spells_records_the_size_concept_promotion():
    """Establishment size is not enterprise size; the proxy must be
    visible."""
    sipp = pd.DataFrame(
        {
            "person_id": ["a"],
            "spell_id": [1],
            "start_month": [pd.Period("2023-01", freq="M")],
            "end_month": [pd.Period("2023-05", freq="M")],
            "industry": ["31"],
            "estab_size_band": ["B50_99"],
            "class_of_worker": ["private"],
            "earnings_share": [1.0],
            "top_earner": [True],
        }
    )
    out = ic1.from_sipp_spells(sipp)
    assert "establishment size" in out.attrs["size_concept"]
    assert "proxy" in out.attrs["size_concept"]


def test_from_sipp_spells_rejects_a_frame_without_the_band_column():
    with pytest.raises(ValueError, match="estab_size_band"):
        ic1.from_sipp_spells(pd.DataFrame({"person_id": ["a"]}))
