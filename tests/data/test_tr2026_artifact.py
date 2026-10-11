"""TR2026 committed input invariants and differential source checks.

Artifact tier: this module reads data/external/tr2026 inputs only. It
never reads PSID or any blind-test outcomes.
"""

import csv
import gzip
import hashlib
import io
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import tr2026
from populace_dynamics.data.life_table import life_expectancy_profile

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "external" / "tr2026"


def _artifact(name):
    return json.loads((DATA_DIR / name).read_text())


def test_hash_pins_and_first_load_verification(tmp_path, monkeypatch):
    tr2026.verify_files()
    for name in tr2026.FILE_SHA256:
        (tmp_path / name).write_bytes((DATA_DIR / name).read_bytes())
    target = tmp_path / "tr2026_parameters.json"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="sha256"):
        tr2026.verify_files(tmp_path)
    monkeypatch.setattr(tr2026, "DATA_DIR", tmp_path)
    tr2026._data.cache_clear()
    tr2026._table.cache_clear()
    with pytest.raises(ValueError, match="sha256"):
        tr2026.tfr(2026)
    tr2026._data.cache_clear()
    tr2026._table.cache_clear()


def test_source_payloads_are_pinned():
    for record in _artifact("sources.json")["sources"].values():
        stored = record["committed_file"]
        if stored:
            raw = (DATA_DIR / stored).read_bytes()
            if stored.endswith(".gz"):
                raw = gzip.decompress(raw)
            assert len(raw) == record["bytes"]
            assert hashlib.sha256(raw).hexdigest() == record["sha256"]


def test_all_coverage_and_published_examples():
    assert len(tr2026.cola_path(1975, 2100)) == 126
    assert len(tr2026.awi(1970, 2100)) == 131
    assert tr2026.cola_path(2025, 2026)[0].percent == 2.8
    assert tr2026.cola_path(2026, 2026)[0].percent == 2.7
    assert tr2026.cpiw_growth(2026) == 2.62
    assert tr2026.awi(2025, 2025)[0].amount == 72025.07
    assert tr2026.tfr(2026) == 1.59
    assert tr2026.tfr(2050) == 1.75
    assert tr2026.asadr(2026, "total") == 769.7
    for year in range(1960, 2101):
        assert np.isfinite(tr2026.cpiw_growth(year))
    for year in range(1940, 2101):
        assert tr2026.tfr(year) > 0
        for group in ("total", "under_65", "65_and_over"):
            assert tr2026.asadr(year, group) > 0
    assert all(entry.amount > 0 for entry in tr2026.awi(1970, 2100))


def test_q_reparse_matches_all_published_cells_and_terminal_age():
    for sex, code in (("male", "M"), ("female", "F")):
        for variant in ("Hist", "Alt2"):
            raw = (
                DATA_DIR
                / "sources"
                / f"DeathProbsE_{code}_{variant}_TR2026.csv"
            ).read_text()
            rows = list(csv.reader(io.StringIO(raw)))[2:]
            for row in rows:
                if not row:
                    continue
                year = int(row[0])
                expected = np.array(row[1:], dtype=float)
                actual = tr2026.death_probability(year, sex)
                np.testing.assert_array_equal(actual, expected)
                assert actual.shape == (120,)
                assert np.all((actual >= 0) & (actual <= 1))
                assert actual[119] == float(row[-1])
                if expected[119] == 1:
                    assert actual[119] == 1
    assert tr2026.death_probability(2030, "male")[119] == 0.949919


def test_q_arrays_and_path_records_are_immutable():
    q = tr2026.death_probability(2030, "female")
    with pytest.raises(ValueError):
        q[0] = 0
    with pytest.raises(ValueError):
        q.setflags(write=True)
    entry = tr2026.awi(2026, 2026)[0]
    with pytest.raises(FrozenInstanceError):
        entry.amount = 0


def test_recomputed_expectancy_matches_published_tables():
    mortality = _artifact("tr2026_death_probabilities.json")
    va4 = {
        row[0]: row[1:]
        for row in _artifact("tr2026_parameters.json")["tables"]["V.A4"][
            "rows"
        ]
    }
    for sex, birth_column, age65_column in (("male", 0, 2), ("female", 1, 3)):
        inputs = mortality["sexes"][sex]["check_inputs_f0_e0_e65"]
        for year_text, (f0, e0, e65) in inputs.items():
            year = int(year_text)
            ex = life_expectancy_profile(
                tr2026.death_probability(year, sex), f0=f0
            )
            assert abs(ex[0] - e0) <= 0.006
            assert abs(ex[65] - e65) <= 0.006
            if year in va4:
                assert abs(ex[0] - va4[year][birth_column]) <= 0.051
                assert abs(ex[65] - va4[year][age65_column]) <= 0.051
    checks = _artifact("transcription_check.json")
    assert checks["all_passed"]
    assert all(check["passed"] for check in checks["checks"])


def test_cola_splice_and_provenance():
    entries = tr2026.cola_path(2035, 2036)
    assert entries[0].percent == entries[1].percent == 2.4
    assert entries[0].source == "tr2026_v_c1_projected"
    assert entries[1].source == "derived_annual_cpiw_cola"
    metadata = tr2026.value_provenance("cola", 2036)
    assert metadata.derived_rule == "post_2035_cola_annual_cpiw"
    assert metadata.source_file == "lr5b1.html"
    assert len(metadata.source_sha256) == 64
    assert tr2026.cola_path(1982, 1983)[0].effective_month == "June"
    assert tr2026.cola_path(1982, 1983)[1].effective_month == "December"
    assert tr2026.cola_path(2025, 2025)[0].source == "tr2026_v_c1_actual"
    assert tr2026.value_provenance("cpiw_growth", 2025).source.endswith(
        "estimated"
    )
    assert tr2026.value_provenance("tfr", 2024).source.endswith("historical")
    assert tr2026.value_provenance("awi", 2025).source.endswith("estimated")
    assert tr2026.value_provenance(
        "asadr", 2023, group="total"
    ).source.endswith("preliminary")
    assert tr2026.value_provenance(
        "asadr", 2023, group="under_65"
    ).source.endswith("historical")
    assert tr2026.value_provenance(
        "asadr", 2024, group="under_65"
    ).source.endswith("preliminary")
    assert tr2026.value_provenance("tfr", 2025).source.endswith("provisional")
    for series in ("cpiw_growth", "awi", "tfr"):
        assert "year 2026" in tr2026.value_provenance(series, 2026).locator
    assert (
        "group total"
        in tr2026.value_provenance("asadr", 2026, group="total").locator
    )
    assert (
        "sex female"
        in tr2026.value_provenance(
            "death_probability", 2026, sex="female"
        ).locator
    )


def test_cpi_index_continuity_around_cola_extension_splice():
    rows = _artifact("tr2026_parameters.json")["tables"]["VI.G1"]["rows"]
    levels = {row[0]: row[3] for row in rows}
    for year in (2035, 2036):
        expected = levels[year - 1] * (1 + tr2026.cpiw_growth(year) / 100)
        # Printed index levels are rounded to .01 and growth to .01 percent.
        assert abs(levels[year] - expected) <= 0.02
    assert tr2026.cola_path(2036, 2036)[0].percent == tr2026.cpiw_growth(2036)


@pytest.mark.parametrize("first,last", [(1974, 1975), (2100, 2101)])
def test_cola_refuses_outside_coverage(first, last):
    with pytest.raises(KeyError):
        tr2026.cola_path(first, last)


@pytest.mark.parametrize(
    "call",
    [
        lambda: tr2026.awi(1969, 1970),
        lambda: tr2026.awi(2101, 2101),
        lambda: tr2026.cpiw_growth(1959),
        lambda: tr2026.cpiw_growth(2101),
        lambda: tr2026.tfr(1939),
        lambda: tr2026.tfr(2101),
        lambda: tr2026.asadr(1939, "total"),
        lambda: tr2026.asadr(2101, "total"),
        lambda: tr2026.death_probability(1899, "male"),
        lambda: tr2026.death_probability(2101, "female"),
    ],
)
def test_refuses_missing_year(call):
    with pytest.raises(KeyError):
        call()


@pytest.mark.parametrize("year", [True, False, 2026.0, "2026", None])
def test_refuses_noninteger_year(year):
    for call in (
        lambda: tr2026.cola_path(year, year),
        lambda: tr2026.awi(year, year),
        lambda: tr2026.cpiw_growth(year),
        lambda: tr2026.tfr(year),
        lambda: tr2026.asadr(year, "total"),
        lambda: tr2026.death_probability(year, "male"),
    ):
        with pytest.raises(ValueError, match="integer"):
            call()


def test_refuses_invalid_selections():
    for call in (
        lambda: tr2026.cola_path(2027, 2026),
        lambda: tr2026.awi(2027, 2026),
        lambda: tr2026.death_probability(2026, "both"),
        lambda: tr2026.asadr(2026, "65+"),
        lambda: tr2026.value_provenance("asadr", 2026),
        lambda: tr2026.value_provenance("death_probability", 2026),
        lambda: tr2026.value_provenance("awi", 2026, sex="male"),
        lambda: tr2026.value_provenance("cola", 2026, group="total"),
        lambda: tr2026.value_provenance("unknown", 2026),
    ):
        with pytest.raises(ValueError):
            call()


@settings(max_examples=25, deadline=None)
@given(st.integers(1975, 2099), st.integers(1, 10))
def test_cola_path_partition_invariant(first, width):
    last = min(2100, first + width)
    middle = (first + last) // 2
    assert tr2026.cola_path(first, last) == tr2026.cola_path(
        first, middle
    ) + tr2026.cola_path(middle + 1, last)


@settings(max_examples=25, deadline=None)
@given(st.integers(1970, 2100))
def test_awi_singleton_and_positive_invariant(year):
    (entry,) = tr2026.awi(year, year)
    assert entry.year == year
    assert entry.amount > 0
    assert entry.source == tr2026.value_provenance("awi", year).source


@settings(max_examples=25, deadline=None)
@given(st.integers(1900, 2100), st.sampled_from(["male", "female"]))
def test_q_probability_and_source_boundary_invariant(year, sex):
    q = tr2026.death_probability(year, sex)
    assert len(q) == 120
    assert np.all(np.isfinite(q))
    assert np.all((q >= 0) & (q <= 1))
    expected = "historical" if year <= 2023 else "alt2"
    assert tr2026.value_provenance(
        "death_probability", year, sex=sex
    ).source.endswith(expected)
