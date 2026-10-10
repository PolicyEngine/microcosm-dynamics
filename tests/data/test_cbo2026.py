"""Artifact invariants for the pinned public CBO2026 baseline inputs."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import cbo2026 as cbo
from populace_dynamics.data import tr2026 as tr
from populace_dynamics.data.life_table import (
    life_expectancy,
    period_life_table,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "external" / "cbo2026"


def _payload(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def test_hash_pins_and_mutation_refusal(tmp_path, monkeypatch):
    cbo.verify_files()
    for name in cbo.FILE_SHA256:
        (tmp_path / name).write_bytes((DATA_DIR / name).read_bytes())
    cbo.verify_files(tmp_path)
    target = tmp_path / "cbo2026_economics.json"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SHA-256"):
        cbo.verify_files(tmp_path)
    cbo._data.cache_clear()
    monkeypatch.setattr(cbo, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        cbo.cpiu_growth(2026)
    cbo._data.cache_clear()


def test_exact_source_coverage_and_positive_inputs():
    demographic = _payload("cbo2026_demographics.json")
    economics = _payload("cbo2026_economics.json")
    years = {str(y) for y in range(2021, 2100)}
    assert set(demographic["asfr"]) == years
    assert set(demographic["mortality"]) == years
    assert set(demographic["published_summary"]) == {
        str(y) for y in range(2026, 2100)
    }
    assert set(economics["long_term"]) == {str(y) for y in range(1996, 2057)}
    assert set(economics["covered"]) == {str(y) for y in range(2026, 2101)}
    assert all(entry.amount > 0 for entry in cbo.awi(2024, 2100))
    for year in range(1996, 2101):
        assert cbo.cpiu_index(year) > 0


def test_retained_source_pins_and_size_policy():
    sources = _payload("sources.json")["sources"]
    retained = []
    for source in sources.values():
        if source["committed_file"] is None:
            continue
        path = DATA_DIR / source["committed_file"]
        retained.append(path.name)
        compressed = path.read_bytes()
        assert (
            hashlib.sha256(compressed).hexdigest()
            == source["compressed_sha256"]
        )
        raw = gzip.decompress(compressed)
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        assert len(raw) == source["bytes"]
        assert len(raw) < 2_000_000
        assert len(compressed) < 500_000
    assert set(retained) == {
        path.name for path in (DATA_DIR / "sources").iterdir()
    }


def test_all_year_mortality_bounds_and_source_terminal_closure():
    for year in range(2021, 2100):
        for sex in cbo.SEXES:
            q = cbo.mortality(year, sex)
            assert q.shape == (120,)
            assert np.isfinite(q).all()
            assert ((q >= 0) & (q <= 1)).all()
            assert q[119] == 1.0
            assert not q.flags.writeable
    with pytest.raises(ValueError, match="read-only"):
        cbo.mortality(2026, "male")[0] = 0.0


def test_q_semantics_reproduce_every_published_life_expectancy():
    checks = _payload("transcription_check.json")
    assert checks["all_passed"]
    semantics = checks["mortality_interpretation"]
    assert semantics["selected"] == "q"
    tolerance = semantics["tolerance_years"]
    assert tolerance == 0.0011
    for year, summary in _payload("cbo2026_demographics.json")[
        "published_summary"
    ].items():
        for age, field in (
            (0, "life_expectancy_birth"),
            (65, "life_expectancy_65"),
        ):
            q_le = []
            m_le = []
            for sex in cbo.SEXES:
                q = cbo.mortality(int(year), sex)
                table = period_life_table(q, f0=0.5)
                q_le.append(table.ex[age])
                # Differential check: column construction vs recursion.
                assert table.ex[age] == pytest.approx(
                    life_expectancy(q, age, f0=0.5), abs=1e-12
                )
                interpreted_m = q / (1.0 + q / 2.0)
                m_le.append(life_expectancy(interpreted_m, age, f0=0.5))
            assert np.mean(q_le) == pytest.approx(
                summary[field], abs=tolerance
            )
            assert abs(np.mean(m_le) - summary[field]) > tolerance


def test_asfr_units_and_published_tfr_rounding():
    for year in range(2021, 2100):
        for place in cbo.PLACES:
            rates = cbo.asfr(year, place)
            assert set(rates) == set(range(14, 50))
            assert all(0 <= value <= 1 for value in rates.values())
        assert sum(cbo.asfr(year).values()) == pytest.approx(
            cbo.tfr(year), abs=0.0023
        )
    raw = _payload("cbo2026_demographics.json")["asfr"]["2026"]["all"]
    assert cbo.asfr(2026)[30] == raw[30 - 14] / 1000.0


def test_cpi_splices_are_continuous_and_extension_is_explicit():
    for year in (2023, 2024, 2036, 2037, 2056, 2057, 2100):
        ratio = cbo.cpiu_index(year) / cbo.cpiu_index(year - 1)
        assert ratio == pytest.approx(1.0 + cbo.cpiu_growth(year) / 100)
    for year in range(2057, 2101):
        assert cbo.cpiu_growth(year) == cbo.cpiu_growth(2056)
        assert cbo.real_earnings_growth(year) == cbo.real_earnings_growth(2056)
    assert (
        "hold_2056_economic_growth"
        in cbo.value_provenance("cpiu_growth", 2057).builder_defaults
    )
    assert cbo.cpiw_growth(2057) == cbo.cpiu_growth(2057)
    assert (
        "cpiw_equals_cpiu_growth"
        in cbo.value_provenance("cpiw_growth", 2057).builder_defaults
    )


def test_awi_anchor_bridge_and_covered_growth_identity():
    economics = _payload("cbo2026_economics.json")
    entries = {entry.year: entry for entry in cbo.awi(2024, 2100)}
    assert entries[2024].amount == economics["awi_anchor"]["amount"]
    assert entries[2024].amount == tr.awi(2024, 2024)[0].amount
    assert entries[2024].source == "tr2026_vi_g1_actual"
    for year in (2025, 2026):
        nominal_growth = (1 + cbo.real_earnings_growth(year) / 100) * (
            1 + cbo.cpiu_growth(year) / 100
        )
        assert entries[year].amount == pytest.approx(
            entries[year - 1].amount * nominal_growth
        )
        assert entries[year].source == "derived_cbo2026_awi_bridge"
    for year in range(2027, 2101):
        current = economics["covered"][str(year)]
        previous = economics["covered"][str(year - 1)]
        ratio = (
            current["covered_earnings_trillions"]
            / current["total_workers_thousands"]
        ) / (
            previous["covered_earnings_trillions"]
            / previous["total_workers_thousands"]
        )
        assert entries[year].amount / entries[year - 1].amount == (
            pytest.approx(ratio)
        )
        assert entries[year].source.startswith("derived_")


@pytest.mark.parametrize(
    "accessor,args",
    [
        (cbo.asfr, (2020,)),
        (cbo.asfr, (2100,)),
        (cbo.asfr, (2026, "unknown")),
        (cbo.mortality, (2020, "male")),
        (cbo.mortality, (2100, "male")),
        (cbo.mortality, (2026, "unknown")),
        (cbo.tfr, (2100,)),
        (cbo.cpiu_growth, (1995,)),
        (cbo.cpiu_growth, (2101,)),
        (cbo.cpiu_index, (2101,)),
        (cbo.cpiw_growth, (2101,)),
        (cbo.real_earnings_growth, (2101,)),
        (cbo.cola_path, (2023, 2030)),
        (cbo.cola_path, (2030, 2029)),
        (cbo.awi, (2023, 2030)),
        (cbo.awi, (2030, 2029)),
        (cbo.value_provenance, ("unknown", 2026)),
    ],
)
def test_refusals(accessor, args):
    with pytest.raises(ValueError):
        accessor(*args)


@pytest.mark.parametrize("bad_year", [True, 2026.0, "2026", None])
def test_year_type_is_strict(bad_year):
    with pytest.raises(ValueError, match="integer"):
        cbo.cpiu_growth(bad_year)


def test_returned_paths_and_metadata_are_immutable():
    cola = cbo.cola_path(2026, 2026)[0]
    assert cola.determination_year == 2026
    assert cola.effective_month == "December"
    assert cola.source.startswith("derived_")
    with pytest.raises(FrozenInstanceError):
        cola.percent = 0.0
    provenance = cbo.value_provenance("asfr", 2026, place="native-born")
    assert provenance.sha256
    assert provenance.locators
    assert "year=2026" in provenance.locators[0]
    assert "place_of_birth=native-born" in provenance.locators[0]
    assert provenance.source == "cbo2026_asfr_native-born"
    with pytest.raises(FrozenInstanceError):
        provenance.source = "changed"
    rates = cbo.asfr(2026)
    original = rates[30]
    rates[30] = 0
    assert cbo.asfr(2026)[30] == original


@pytest.mark.parametrize(
    "series,qualifiers",
    [
        ("asfr", {"sex": "male"}),
        ("mortality", {"sex": "male", "place": "foreign-born"}),
        ("tfr", {"sex": "bad"}),
        ("cpiu_growth", {"place": "foreign-born"}),
    ],
)
def test_provenance_refuses_irrelevant_group_qualifiers(series, qualifiers):
    with pytest.raises(ValueError, match="qualifier"):
        cbo.value_provenance(series, 2026, **qualifiers)


@settings(deadline=None, max_examples=20)
@given(
    first=st.integers(2024, 2099),
    width=st.integers(0, 10),
)
def test_path_partition_invariant(first, width):
    last = min(2100, first + width)
    middle = (first + last) // 2
    for accessor in (cbo.awi, cbo.cola_path):
        full = accessor(first, last)
        assert len(full) == last - first + 1
        if middle < last:
            assert full == accessor(first, middle) + accessor(middle + 1, last)


@settings(deadline=None, max_examples=20)
@given(year=st.integers(2021, 2099), place=st.sampled_from(cbo.PLACES))
def test_asfr_conversion_invariant(year, place):
    rates = cbo.asfr(year, place)
    printed = _payload("cbo2026_demographics.json")["asfr"][str(year)][place]
    assert [rates[age] * 1000 for age in range(14, 50)] == pytest.approx(
        printed, abs=1e-12
    )


def test_captured_source_reparse_and_cdx_digest_checks():
    script = ROOT / "scripts" / "extract_cbo2026_parameters.py"
    spec = importlib.util.spec_from_file_location("extract_cbo2026", script)
    extractor = importlib.util.module_from_spec(spec)
    # The frozen Source dataclass needs its defining module registered.
    import sys

    sys.modules[spec.name] = extractor
    spec.loader.exec_module(extractor)
    if not extractor.DEFAULT_INPUTS.is_dir():
        pytest.skip(
            "captured inputs required for external-source transcription"
        )
    outputs = extractor.build_all()
    for name, text in outputs.items():
        assert (DATA_DIR / name).read_text(encoding="utf-8") == text
    sources = json.loads(outputs["sources.json"])["sources"]
    wayback = [source for source in sources.values() if source["cdx_sha1_b32"]]
    assert len(wayback) == 4
    assert all(source["cdx_digest_matches"] for source in wayback)
