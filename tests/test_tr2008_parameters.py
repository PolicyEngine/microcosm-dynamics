"""Pins and behavior of the committed TR2008 parameter capture.

Spot values below were read directly off the 2008 Trustees Report pages
named in each comment during extraction review; the transcription check in
``transcription_check.json`` covers every other table cell.  Values labeled
INVENTED exist only to exercise splice arithmetic.
"""

from __future__ import annotations

import base64
import copy
import dataclasses
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from populace_dynamics.data import tr2008

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "external" / "tr2008"
SOURCES = DATA / "sources"
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import extract_tr2008_parameters as extractor  # noqa: E402

REVIEWED_SHA256 = {
    "tr2008_report.json": (
        "c16161f1ee99d94d97648da078d686325fb05a0d44653b76bc609158e63f6d62"
    ),
    "tr2008_single_year.json": (
        "6ada61d3f8a3b693939763cbe142d191d81468f73022fb3450ab69f817ab596e"
    ),
    "ssa_2008_vintage.json": (
        "78c5e55b29615e21f60dc6345572ab06206245246394e2a2791d82358c45d7d7"
    ),
    "actuarial_study_118.json": (
        "0cff75e67257f75630f1fb2cbdf7e6b266f47109b5c95e56a976a195f161aa9b"
    ),
    "transcription_check.json": (
        "18066387c4879135978608c53a2f5309e083a2fc89acc7469399712f2ec9b45d"
    ),
    "sources.json": (
        "ac09e00eadb5935f36a6a52a808b0a49bd5c76dac0d594e0fb820bbb3373fbc5"
    ),
}
TRANSCRIPTION_CELLS = 10441


def _json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- pins


@pytest.mark.parametrize("name", sorted(REVIEWED_SHA256))
def test__committed_json__matches_reviewed_sha256(name):
    digest = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
    assert digest == REVIEWED_SHA256[name]


def test__loader_pins__equal_the_reviewed_pins():
    assert dict(tr2008.FILE_SHA256) == REVIEWED_SHA256
    tr2008.verify_files()


def test__loader__refuses_a_tampered_file(tmp_path):
    for name in REVIEWED_SHA256:
        shutil.copy(DATA / name, tmp_path / name)
    target = tmp_path / "tr2008_report.json"
    target.write_text(target.read_text() + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="tr2008_report.json sha256"):
        tr2008.verify_files(tmp_path)


def test__source_captures__match_manifest_and_wayback_digests():
    manifest = _json("sources.json")["wayback_captures"]
    committed = sorted(path.name for path in SOURCES.iterdir())
    assert committed == sorted(f"{name}.gz" for name in manifest)
    assert set(manifest) == set(extractor.WAYBACK_SOURCES)
    for name, entry in manifest.items():
        payload = gzip.decompress((SOURCES / f"{name}.gz").read_bytes())
        assert len(payload) == entry["bytes"]
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
        sha1_b32 = base64.b32encode(hashlib.sha1(payload).digest()).decode()
        assert sha1_b32 == entry["wayback_sha1_b32"]
        assert entry["capture_url"] == (
            f"https://web.archive.org/web/{entry['wayback_timestamp']}id_/"
            f"{entry['original_url']}"
        )


def test__report_pdf__identity_is_recorded_consistently():
    sources = _json("sources.json")["report_pdf"]
    document = _json("tr2008_report.json")["document"]
    assert sources["sha256"] == document["pdf_sha256"] == extractor.PDF_SHA256
    assert sources["wayback_sha1_b32"] == document["wayback_sha1_b32"]
    assert sources["wayback_timestamp"] == "20100331224612"
    report = _json("tr2008_report.json")
    assert (report["trustees_report_year"], report["vintage_year"]) == (
        2008,
        2008,
    )
    assert document["house_referral_date_pdf_page_1"] == "April 10, 2008"


def test__study_118_pdf__identity_is_recorded_consistently():
    recorded = _json("sources.json")["actuarial_study_118_pdf"]
    document = _json("actuarial_study_118.json")["document"]
    assert (
        recorded["sha256"] == document["pdf_sha256"] == extractor.AS118_SHA256
    )
    assert recorded["wayback_sha1_b32"] == document["wayback_sha1_b32"]
    assert recorded["wayback_timestamp"] == "20080326052706"
    assert recorded["bytes"] == document["pdf_bytes"] == 679311
    assert document["published"] == "June 2005"
    located = _json("sources.json")["located_not_committed"]
    assert "actuarial_study_118" not in located
    assert set(located) == {
        "actuarial_study_120",
        "tr08_long_range_methods_documentation",
        "tr08_release_pdf",
    }
    # Located by CDX digest only: never downloaded, so no payload digest.
    documentation = located["tr08_long_range_methods_documentation"]
    assert documentation["examined"] is False
    assert documentation["sha256"] is None and documentation["bytes"] is None
    assert documentation["wayback_sha1_b32"] == (
        "EUNJVAMTFCUTPS4MB2LXXSYPVFU5XEVG"
    )


def test__transcription_check__passed_on_every_compared_cell():
    checks = _json("transcription_check.json")
    assert checks["all_passed"] is True
    assert checks["cells_compared"] == TRANSCRIPTION_CELLS
    assert all(check["mismatches"] == [] for check in checks["checks"])
    ids = {check["id"] for check in checks["checks"]}
    for table in (
        "V.C1",
        "V.B1",
        "VI.F6",
        "II.C1",
        "V.A1",
        "V.A3",
        "V.A4",
        "V.C5",
    ):
        assert f"{table}_pdf_vs_html" in ids
    assert {
        "text_values_pdf_vs_html",
        "AS118_death_probability_vs_survival",
        "AS118_recovery_probability_vs_survival",
        "AS118_old_age_death_vs_survival",
        "AS118_combined_equals_death_plus_recovery",
        "AS118_table5_arithmetic",
        "AS118_table6_arithmetic",
        "AS118_table4_consistency",
    } <= ids
    by_id = {check["id"]: check for check in checks["checks"]}
    # Every text-stated value was re-read from the report's HTML chapter.
    text_cells = sum(
        len(entry["values"])
        for entry in _json("tr2008_report.json")["text_values"]
    )
    assert by_id["text_values_pdf_vs_html"]["cells_compared"] == (
        text_cells + 1
    )
    death_survival = by_id["AS118_death_probability_vs_survival"]
    assert death_survival["largest_difference"] == 0


def test__extractor__reproduces_committed_outputs_from_the_pdfs():
    pdf = Path(os.environ.get(extractor.PDF_ENV, extractor.DEFAULT_PDF))
    study = Path(
        os.environ.get(extractor.AS118_ENV, extractor.AS118_DEFAULT_PDF)
    )
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext unavailable")
    if not pdf.exists() or not study.exists():
        pytest.skip("TR2008 or Actuarial Study 118 PDF unavailable")
    arguments = ["--check", "--pdf", str(pdf), "--as118-pdf", str(study)]
    assert extractor.main(arguments) == 0


# ---------------------------------------------------- independent re-parse
#
# A second, deliberately small parser of the same PDF text layer.  It
# shares no parsing code with scripts/extract_tr2008_parameters.py (it
# takes only the default PDF locations from the extractor and the pinned
# PDF digests from sources.json), so a defect in the extractor's row,
# section or footnote rules would surface here.  It is
# most useful for Study 118 Table 4, whose age-specific cells have no
# second rendering and no arithmetic identity.  It cannot catch an error
# in pdftotext's own text layer.

_REPARSE_SECTIONS = {
    "Historical data:": "historical",
    "Intermediate:": "intermediate",
    "Low Cost:": "low_cost",
    "High Cost:": "high_cost",
}
_REPARSE_ROW = re.compile(r"^(\d{4})\s*(?:\.\s*)+(\S.*)$")


def _reparse_pdf(source_key: str, env: str, default: Path) -> Path:
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext unavailable")
    path = Path(os.environ.get(env, default))
    if not path.exists():
        pytest.skip(f"{path.name} unavailable")
    recorded = _json("sources.json")[source_key]["sha256"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == recorded
    return path


def _reparse_page(path: Path, page: int) -> list[str]:
    text = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), path, "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line.strip() for line in text.splitlines()]


def _reparse_cell(token: str) -> float:
    return float(token.replace("$", "").replace(",", ""))


def _reparse_year_rows(lines: list[str]):
    section = None
    for line in lines:
        if line in _REPARSE_SECTIONS:
            section = _REPARSE_SECTIONS[line]
            continue
        match = _REPARSE_ROW.match(line)
        if match and section is not None:
            yield section, int(match.group(1)), match.group(2).split()


def test__independent_reparse__v_c1_vi_f6_and_ii_c1_equal_the_reader():
    pdf = _reparse_pdf("report_pdf", extractor.PDF_ENV, extractor.DEFAULT_PDF)
    projected = set(range(2007, 2018))
    # V.C1, PDF pp.110-111: COLA, AWI and AWI increase.  A leading "6" or
    # "7" token is a footnote marker (1999 and 2007 COLAs).
    v_c1 = {
        section: {row["year"]: row for row in rows}
        for section, rows in _json("tr2008_report.json")["tables"]["V.C1"][
            "sections"
        ].items()
    }
    seen: dict[str, set[int]] = {}
    lines = _reparse_page(pdf, 110) + _reparse_page(pdf, 111)
    for section, year, tokens in _reparse_year_rows(lines):
        if tokens[0] in ("6", "7"):
            tokens = tokens[1:]
        cola, amount, increase = map(_reparse_cell, tokens[:3])
        seen.setdefault(section, set()).add(year)
        alternatives = (
            tr2008.ALTERNATIVES if section == "historical" else (section,)
        )
        for alternative in alternatives:
            assert tr2008.cola_percent(year, alternative=alternative) == cola
            assert tr2008.awi(year, alternative=alternative) == amount
        assert v_c1[section][year]["awi_increase_percent"] == increase
    assert seen == {
        "historical": set(range(1975, 2007)),
        **{alternative: projected for alternative in tr2008.ALTERNATIVES},
    }
    # VI.F6, PDF pp.192-193: adjusted CPI and AWI.
    seen = {}
    lines = _reparse_page(pdf, 192) + _reparse_page(pdf, 193)
    for section, year, tokens in _reparse_year_rows(lines):
        cpi, amount = map(_reparse_cell, tokens[:2])
        seen.setdefault(section, set()).add(year)
        assert tr2008.adjusted_cpi(year, alternative=section) == cpi
        assert tr2008.awi(year, alternative=section) == amount
    five_yearly = set(range(2020, 2086, 5))
    assert seen == {
        alternative: projected | five_yearly
        for alternative in tr2008.ALTERNATIVES
    }
    # II.C1, PDF p.14: the last three tokens of each labeled row.
    labels = {
        "Total fertility rate": "total_fertility_rate",
        "adjusted death rates from 2032": "death_rate_reduction_2032_2082",
        "the period 2008-82": "net_immigration_thousands_2008_82",
        "Productivity": "productivity",
        "Average wage in covered": "average_covered_wage",
        "Consumer Price Index": "cpi",
        "Real-wage differential": "real_wage_differential",
        "Unemployment rate": "unemployment_rate",
        "real interest rate": "real_interest_rate",
    }
    found = set()
    for line in _reparse_page(pdf, 14):
        for label, field in labels.items():
            if label in line and ". ." in line:
                values = map(_reparse_cell, line.split()[-3:])
                for alternative, value in zip(
                    tr2008.ALTERNATIVES, values, strict=True
                ):
                    ultimate = tr2008.ultimate_assumptions(alternative)
                    assert getattr(ultimate, field) == value, field
                found.add(field)
    assert found == set(labels.values())


def test__independent_reparse__study_118_tables_equal_the_reader():
    pdf = _reparse_pdf(
        "actuarial_study_118_pdf",
        extractor.AS118_ENV,
        extractor.AS118_DEFAULT_PDF,
    )
    # Table 4, PDF p.29: eleven age groups, gross and adjusted, by sex.
    seen: dict[str, set[int]] = {}
    sex = None
    for line in _reparse_page(pdf, 29):
        if line in ("Male", "Female", "Total"):
            sex = line.lower()
            continue
        tokens = line.split()
        if sex is None or not tokens or not re.fullmatch(r"\d{4}", tokens[0]):
            continue
        values = [float(token) for token in tokens[1:]]
        row = tr2008.di_incidence_by_age(int(tokens[0]), sex=sex)
        assert values == [*row.by_age.values(), row.gross, row.adjusted]
        seen.setdefault(sex, set()).add(int(tokens[0]))
    assert seen == {
        sex: set(range(1980, 2005)) for sex in ("male", "female", "total")
    }
    # Tables 7A/7B (death) and 14A/14B (recovery): select ages 16-64,
    # durations 0-9 and "10 or more", then the attained age.  An em dash
    # marks an untabulated cell.
    grids = {
        35: ("death", "male"),
        36: ("death", "female"),
        53: ("recovery", "male"),
        54: ("recovery", "female"),
    }
    for page, (cause, sex) in grids.items():
        select_ages = []
        for line in _reparse_page(pdf, page):
            tokens = line.split()
            if len(tokens) != 13 or not tokens[0].isdigit():
                continue
            select_age = int(tokens[0])
            assert int(tokens[12]) == select_age + 10
            for duration, token in enumerate(tokens[1:12]):
                expected = None if token == "\u2014" else float(token)
                assert (
                    tr2008.di_termination_probability(
                        cause,
                        sex=sex,
                        select_age=select_age,
                        duration=duration,
                    )
                    == expected
                ), (page, select_age, duration)
            select_ages.append(select_age)
        assert select_ages == list(range(16, 65)), page


# ---------------------------------------------------------------- locators


def test__table_locators__carry_pdf_and_printed_pages():
    tables = _json("tr2008_report.json")["tables"]
    expected = {
        "II.C1": [14],
        "V.A1": [88, 89],
        "V.A3": [93],
        "V.A4": [94],
        "V.B1": [100, 101],
        "V.C1": [110, 111],
        "V.C5": [132, 133],
        "VI.F6": [192, 193],
    }
    for table, pages in expected.items():
        assert tables[table]["pdf_pages"] == pages
        assert tables[table]["printed_pages"] == [page - 8 for page in pages]


# ---------------------------------------------------------------- COLA


def test__cola__v_c1_spot_values():
    # V.C1, PDF p.110 (printed p.102) and p.111 (printed p.103).
    assert tr2008.cola_percent(1999) == 2.5  # footnote 6
    assert tr2008.cola_percent(2006) == 3.3
    assert tr2008.cola_percent(2007) == 2.3  # footnote 7, actual
    assert tr2008.cola_percent(2008) == 2.7
    assert tr2008.cola_percent(2009) == 2.5
    assert tr2008.cola_percent(2009, alternative="low_cost") == 1.9
    assert tr2008.cola_percent(2012, alternative="high_cost") == 5.9


def test__cola__tr2008_history_equals_the_committed_ssa_cola_series():
    # Independent source: data/external/ssa_cola_history.json (SSA OACT
    # COLA series).  TR2008's historical rows and 2007 actual must agree;
    # its 2008-2010 projections differ from what was later realized.
    ssa_history = json.loads(
        (ROOT / "data" / "external" / "ssa_cola_history.json").read_text()
    )["data"]
    for year in range(1975, 2008):
        assert tr2008.cola_percent(year) == ssa_history[str(year)], year
    realized = [ssa_history[str(year)] for year in (2008, 2009, 2010)]
    projected = [tr2008.cola_percent(year) for year in (2008, 2009, 2010)]
    assert realized == [5.8, 0.0, 0.0]
    assert projected == [2.7, 2.5, 2.8]


def test__cola_path__default_is_the_plan_primary_rate_path():
    path = tr2008.cola_path(2006, 2030)
    by_year = {entry.determination_year: entry for entry in path}
    assert by_year[2006].source == "tr2008_v_c1_historical"
    assert by_year[2007].source == "tr2008_v_c1_actual"
    assert by_year[2008].source == "tr2008_v_c1_projected"
    assert all(by_year[y].percent == 2.8 for y in range(2010, 2031))
    assert all(
        by_year[y].source == "tr2008_v_c1_projected" for y in range(2010, 2018)
    )
    assert all(
        by_year[y].source == "derived_ultimate_cpi" for y in range(2018, 2031)
    )
    assert {entry.effective_month for entry in path} == {"December"}
    assert tr2008.cola_path(1982, 1983)[0].effective_month == "June"


@pytest.mark.parametrize(
    ("alternative", "ultimate"),
    [("intermediate", 2.8), ("low_cost", 1.8), ("high_cost", 3.8)],
)
def test__derived_post_2017_cola__matches_every_single_year_cpi_change(
    alternative, ultimate
):
    assert tr2008.ultimate_assumptions(alternative).cpi == ultimate
    assert tr2008.cola_percent(2017, alternative=alternative) == ultimate
    for year in range(2018, 2083):
        cpi = tr2008.economic_assumptions(year, alternative=alternative).cpi
        assert cpi == ultimate
    # VI.F6's adjusted CPI (single-year table) grows at the ultimate rate
    # in every year 2018-2085, the last year TR2008 projects.
    for year in range(2018, tr2008.LAST_PROJECTION_YEAR + 1):
        index = tr2008.adjusted_cpi(year, alternative=alternative)
        prior = tr2008.adjusted_cpi(year - 1, alternative=alternative)
        assert round(100 * (index / prior - 1), 1) == ultimate, year
        assert tr2008.cola_percent(year, alternative=alternative) == ultimate


def test__cola_path__refuses_years_after_the_tr2008_projection():
    # Regression: the derived ultimate CPI was returned for any year after
    # 2017 (2086, 2200, ...), although TR2008 projects nothing after 2085.
    assert tr2008.LAST_PROJECTION_YEAR == 2085
    with pytest.raises(KeyError, match="VI.F6 has no adjusted CPI for 2086"):
        tr2008.adjusted_cpi(2086)
    for alternative in tr2008.ALTERNATIVES:
        with pytest.raises(KeyError, match="nothing after 2085"):
            tr2008.cola_percent(2086, alternative=alternative)
    with pytest.raises(KeyError, match="nothing after 2085"):
        tr2008.cola_path(2080, 2200)
    path = tr2008.cola_path(2080, 2085)
    assert [entry.source for entry in path] == ["derived_ultimate_cpi"] * 6


def test__economic_assumptions__labels_the_2007_intermediate_estimate():
    # Regression: single-year V.B1 footnote 2 says the 2007 values are
    # estimates that vary by alternative and are shown for the intermediate
    # alternative only, but every alternative's 2007 row was tagged as
    # plain history.
    historical = _json("tr2008_single_year.json")["tables"]["V.B1"][
        "sections"
    ]["historical"]
    assert [row["year"] for row in historical if row.get("footnote")] == [2007]
    for alternative in tr2008.ALTERNATIVES:
        row = tr2008.economic_assumptions(2007, alternative=alternative)
        assert row.source == (
            "tr2008_single_year_v_b1/historical_estimate_intermediate_only"
        )
        assert row.cpi == 2.8
    assert tr2008.economic_assumptions(2006).source == (
        "tr2008_single_year_v_b1/historical"
    )
    assert tr2008.economic_assumptions(2008).source == (
        "tr2008_single_year_v_b1/intermediate"
    )


def test__cola_path__strict_mode_and_bounds():
    with pytest.raises(KeyError, match="post_2017='none'"):
        tr2008.cola_path(2017, 2018, post_2017="none")
    with pytest.raises(KeyError, match="no COLA for 1974"):
        tr2008.cola_percent(1974)
    with pytest.raises(ValueError, match="alternative must be one of"):
        tr2008.cola_path(2008, 2009, alternative="II")
    with pytest.raises(ValueError, match="together"):
        tr2008.cola_path(2008, 2009, realized={2008: 1.0})
    # Regression: an unknown post_2017 value was accepted silently for
    # printed years and misreported as a missing V.C1 row after 2017.
    for first, last in ((2008, 2009), (2017, 2018)):
        with pytest.raises(ValueError, match="post_2017 must be one of"):
            tr2008.cola_path(first, last, post_2017="ultimate")
    with pytest.raises(ValueError, match="post_2017 must be one of"):
        tr2008.cola_percent(2009, post_2017="cpi")


def test__cola_path__realized_splice_uses_caller_values_only_through_cutoff():
    invented_realized = {2008: 9.9, 2009: 0.1}  # INVENTED
    path = tr2008.cola_path(
        2008, 2011, realized=invented_realized, last_realized_year=2009
    )
    assert [entry.percent for entry in path] == [9.9, 0.1, 2.8, 2.8]
    assert [entry.source for entry in path[:2]] == ["realized_splice"] * 2
    with pytest.raises(KeyError, match="realized COLA missing for 2007"):
        tr2008.cola_path(
            2007, 2008, realized=invented_realized, last_realized_year=2009
        )


# ---------------------------------------------------------------- AWI


def test__awi__spot_values_across_sources():
    assert tr2008.awi(1975) == 8630.92  # V.C1 p.102
    assert tr2008.awi(2006) == 38651.41  # V.C1 p.102, last historical
    assert tr2008.awi(2017) == 59376.44  # V.C1 p.102
    assert tr2008.awi(2020) == 66519.41  # VI.F6 p.184
    assert tr2008.awi(2030) == 97201.39  # VI.F6 p.184
    assert tr2008.awi(2030, alternative="low_cost") == 87706.73  # p.184
    assert tr2008.awi(2030, alternative="high_cost") == 110813.91  # p.185
    assert tr2008.awi(2018) == 61660.93  # single-year VI.F6 only


def test__awi_path__default_sources_and_coverage_to_2030():
    path = tr2008.awi_path(2005, 2030)
    sources = {entry.year: entry.source for entry in path}
    assert sources[2006] == "tr2008_v_c1_historical"
    assert sources[2007] == "tr2008_v_c1_projected"
    assert sources[2017] == "tr2008_v_c1_projected"
    assert sources[2018] == "tr2008_single_year_vi_f6"
    assert [entry.year for entry in path] == list(range(2005, 2031))


def test__contribution_benefit_base_path__v_c1_spot_values_and_sources():
    # V.C1, PDF p.110 (printed p.102): $14,100 (1975), 94,200 (2006),
    # 97,500 and 102,000 (2007-2008, footnote 7), then projections.
    path = {
        entry.year: entry
        for entry in tr2008.contribution_benefit_base_path(1975, 2017)
    }
    assert list(path) == list(range(1975, 2018))
    assert path[1975].amount == 14_100.0
    assert path[2006].amount == 94_200.0
    assert path[2007].amount == 97_500.0
    assert path[2008].amount == 102_000.0
    assert path[2009].amount == 106_500.0
    assert path[2010].amount == 110_700.0
    assert path[2017].amount == 145_500.0
    assert {path[year].source for year in range(1975, 2007)} == {
        "tr2008_v_c1_historical"
    }
    assert path[2007].source == path[2008].source == "tr2008_v_c1_actual"
    assert {path[year].source for year in range(2009, 2018)} == {
        "tr2008_v_c1_projected"
    }
    (low,) = tr2008.contribution_benefit_base_path(
        2010, 2010, alternative="low_cost"
    )
    (high,) = tr2008.contribution_benefit_base_path(
        2010, 2010, alternative="high_cost"
    )
    assert (low.amount, high.amount) == (111_300.0, 108_900.0)
    with pytest.raises(KeyError, match="1974"):
        tr2008.contribution_benefit_base_path(1974, 1975)
    with pytest.raises(KeyError, match="2018"):
        tr2008.contribution_benefit_base_path(2017, 2018)
    with pytest.raises(ValueError, match="first_year"):
        tr2008.contribution_benefit_base_path(2010, 2009)


def test__awi_path__splice_chains_tr2008_growth_onto_realized_level():
    invented_realized = {2008: 50000.0}  # INVENTED
    path = tr2008.awi_path(
        2008, 2030, realized=invented_realized, last_realized_year=2008
    )
    assert path[0].amount == 50000.0
    expected_2030 = 50000.0 * tr2008.awi(2030) / tr2008.awi(2008)
    assert path[-1].amount == pytest.approx(expected_2030, rel=1e-12)
    assert path[-1].source == "tr2008_single_year_vi_f6_growth_on_realized"


# ---------------------------------------------------------------- economics


def test__ultimate_assumptions__ii_c1_row_values():
    # II.C1, PDF p.14 (printed p.6).
    intermediate = tr2008.ultimate_assumptions()
    assert intermediate.average_covered_wage == 3.9
    assert intermediate.real_wage_differential == 1.1
    assert intermediate.death_rate_reduction_2032_2082 == 0.73
    assert tr2008.ultimate_assumptions("low_cost").cpi == 1.8
    assert tr2008.ultimate_assumptions("high_cost").average_covered_wage == 4.4


def test__adjusted_cpi__is_indexed_to_2008():
    assert tr2008.adjusted_cpi(2008) == 100.0
    assert tr2008.adjusted_cpi(2030) == 183.02  # VI.F6 p.184


# ---------------------------------------------------------------- mortality


def test__mortality_summaries__v_a1_v_a3_v_a4_spot_values():
    # V.A1 p.80: 2030 intermediate; V.A3 p.85; V.A4 p.86.
    assert tr2008.age_sex_adjusted_death_rate(2030) == 689.8
    assert tr2008.age_sex_adjusted_death_rate(2030, group="under_65") == 173.3
    assert (
        tr2008.age_sex_adjusted_death_rate(2030, group="65_and_over") == 4327.1
    )
    assert tr2008.age_sex_adjusted_death_rate(2004) == 819.9
    assert tr2008.period_life_expectancy(2030, sex="male", age=0) == 78.0
    assert tr2008.period_life_expectancy(2030, sex="female", age=65) == 20.3
    assert tr2008.period_life_expectancy(1990, sex="male", age=65) == 15.1
    assert (
        tr2008.cohort_life_expectancy(
            1945, sex="female", age=0, alternative="high_cost"
        )
        == 78.0
    )


def test__period_life_table_2004__spot_values_and_shape():
    male = tr2008.period_life_table_2004("male")
    female = tr2008.period_life_table_2004("female")
    assert [row.age for row in male] == list(range(120))
    assert (male[0].qx, male[0].lx, male[0].ex) == (0.007474, 100000, 74.83)
    assert (female[0].qx, female[0].ex) == (0.006091, 79.96)
    assert (male[65].qx, male[65].ex) == (0.017976, 16.67)
    assert all(0 < row.qx < 1 for row in male + female)


def test__mortality_improvement_ratio__is_a_broad_group_asadr_ratio():
    assert tr2008.mortality_improvement_ratio(2004, 30) == 1.0
    assert tr2008.mortality_improvement_ratio(2030, 64) == pytest.approx(
        173.3 / 234.8
    )
    assert tr2008.mortality_improvement_ratio(2030, 65) == pytest.approx(
        4327.1 / 4940.6
    )
    with pytest.raises(ValueError, match="non-negative"):
        tr2008.mortality_improvement_ratio(2030, -1)


@pytest.mark.parametrize(
    ("alternative", "last_year_above_one"),
    [("intermediate", 2012), ("low_cost", 2024), ("high_cost", 2009)],
)
def test__mortality_improvement_ratio__base_2004_raises_65_plus_at_first(
    alternative, last_year_above_one
):
    # Recorded in the base_year ruling: V.A1's 2004 rate at 65+ (4,940.6,
    # p.80) is below its 2003 value and 2005-2007 estimates, so the
    # default base makes 65+ mortality rise above the 2004 table first.
    ratio = tr2008.mortality_improvement_ratio
    above = [
        year
        for year in range(2005, 2086)
        if ratio(year, 70, alternative=alternative) > 1
    ]
    assert above == list(range(2005, last_year_above_one + 1))
    assert all(
        ratio(year, 40, alternative=alternative) < 1
        for year in range(2005, 2086)
    )
    assert round(ratio(2010, 70), 4) == 1.0127
    (ruling,) = (
        r for r in tr2008.PENDING_RULINGS if r.parameter == "base_year"
    )
    assert "2005-2012" in ruling.default_basis


# ---------------------------------------------------------------- DI


def test__di_text_assumptions__report_values_and_locators():
    incidence = tr2008.text_assumption(
        "di_ultimate_incidence_per_1000_exposed"
    )
    assert incidence.pdf_pages == (127,) and incidence.printed_pages == (119,)
    assert (
        incidence.values["intermediate"],
        incidence.values["low_cost"],
        incidence.values["high_cost"],
    ) == (5.2, 4.2, 6.2)
    recovery = tr2008.text_assumption("di_ultimate_recovery_per_1000")
    assert recovery.values["intermediate"] == 10.8
    assert recovery.values["ultimate_reached"] == 2027
    deaths = tr2008.text_assumption("di_death_rate_short_range_per_1000")
    assert (deaths.values["2007"], deaths.values["2017"]) == (27.9, 23.9)
    assert deaths.pdf_pages == (128, 129)
    prevalence = tr2008.text_assumption(
        "di_prevalence_age_sex_adjusted_per_1000"
    )
    assert prevalence.values["intermediate_2085"] == 47.4


def test__di_series__cover_1970_2085_with_projected_flags():
    for kind in ("incidence", "termination", "prevalence"):
        series = tr2008.di_rates(kind)
        assert [rate.year for rate in series] == list(range(1970, 2086))
        assert [rate.projected for rate in series] == [
            year >= 2008 for year in range(1970, 2086)
        ]
    conversions = tr2008.di_conversion_ratios()
    assert [rate.year for rate in conversions] == list(range(1970, 2086))


def test__di_conversion_ratios__both_bases_and_refuses_an_unknown_basis():
    # Figure V.C5 plot points, 2030 (tr08_LD_figVC5 capture).
    adjusted = {r.year: r.value for r in tr2008.di_conversion_ratios()}
    gross = {r.year: r.value for r in tr2008.di_conversion_ratios("gross")}
    assert (adjusted[2030], gross[2030]) == (40.58, 64.79)
    # Regression: any basis other than "gross" silently returned the
    # age-sex-adjusted ratios.
    for basis in ("adjusted", "Gross", "age-sex-adjusted"):
        with pytest.raises(ValueError, match="unknown basis"):
            tr2008.di_conversion_ratios(basis)


def test__di_beneficiaries__v_c5_spot_values():
    # V.C5 p.124-125.
    row = tr2008.di_beneficiaries(2030)
    assert row.disabled_workers_thousands == 10060
    assert row.prevalence_age_sex_adjusted_per_1000 == 44
    assert tr2008.di_beneficiaries(2007).disabled_workers_thousands == 7099
    high = tr2008.di_beneficiaries(2030, alternative="high_cost")
    assert high.disabled_workers_thousands == 12023


def test__ssa_2008_tables__are_the_captured_captions():
    table20 = tr2008.ssa_2008_table("di_asr_2008", "20")
    assert "Table 20. Number, average primary insurance amount" in (
        table20.caption
    )
    assert table20.rows[2][:2] == ("All disabled workers", "7,426,691")
    insured = tr2008.ssa_2008_table("supplement_2008", "Table 4.C2")
    assert insured.caption.startswith(
        "Table 4.C2—Estimated number, insured status, sex, and age"
    )
    data = _json("ssa_2008_vintage.json")
    assert data["period_life_table_2004"][
        "identical_to_supplement_2008_table_4c6"
    ]


def test__ssa_2008_tables__include_tables_2_and_57_and_agree_on_the_total():
    # DI ASR 2008 Tables 2 (sect01a) and 57 (sect03g): single-digit table
    # ids were silently skipped before the caption regex was fixed.
    table2 = tr2008.ssa_2008_table("di_asr_2008", "2")
    assert table2.caption.endswith(
        "Table 2. Average monthly benefit, by basis of entitlement, age, "
        "and sex, December 2008"
    )
    assert table2.rows[3] == (
        "Total",
        "7,426,691",
        "1,063.10",
        "3,924,524",
        "1,190.70",
        "3,502,167",
        "920.20",
    )
    table57 = tr2008.ssa_2008_table("di_asr_2008", "57")
    assert "Table 57. Distribution, by sex and age, 2008" in table57.caption
    assert table57.rows[3] == (
        "Total",
        "7,426,691",
        "38,209",
        "0.5",
        "37,711",
        "0.5",
    )
    # Three tables, one December 2008 disabled-worker count.
    table20 = tr2008.ssa_2008_table("di_asr_2008", "20")
    assert table20.rows[2][1] == table2.rows[3][1] == table57.rows[3][1]


# ------------------------------------------------- Actuarial Study 118


def test__study_118_locators__carry_pdf_and_printed_pages():
    tables = _json("actuarial_study_118.json")["tables"]
    expected = {
        "4": 29,
        "5": 30,
        "6": 31,
        "7A": 35,
        "7B": 36,
        "7C": 37,
        "8A": 38,
        "8B": 39,
        "8C": 40,
        "14A": 53,
        "14B": 54,
        "15A": 55,
        "15B": 56,
        "21A": 67,
        "21B": 68,
    }
    assert {key: table["pdf_page"] for key, table in tables.items()} == (
        expected
    )
    for table in tables.values():
        assert table["printed_page"] == table["pdf_page"] - 12


def test__di_termination_probability__select_period_spot_values():
    # Study 118 Table 7A p.35 (printed 23), 7B p.36, 14A p.53, 14B p.54.
    death = tr2008.di_termination_probability
    assert death("death", sex="male", select_age=16, duration=0) == 0.004751
    assert death("death", sex="male", select_age=64, duration=0) == 0.178043
    assert death("death", sex="male", select_age=35, duration=10) == 0.016554
    assert death("death", sex="female", select_age=64, duration=9) == 0.070448
    assert death("recovery", sex="male", select_age=16, duration=4) == 0.123602
    assert (
        death("recovery", sex="female", select_age=64, duration=0) == 0.000453
    )
    assert death("recovery", sex="male", select_age=60, duration=4) == 0.000882


def test__di_termination_probability__reads_ultimate_column_and_table_7c():
    probability = tr2008.di_termination_probability
    # Duration 15 at select 30 is attained 45: ultimate cell of select 35.
    assert probability(
        "death", sex="male", select_age=30, duration=15
    ) == probability("death", sex="male", select_age=35, duration=10)
    assert (
        probability("death", sex="male", select_age=30, duration=15)
        == 0.016554
    )
    # Recovery, select 40, duration 12: ultimate cell of select 42 (14A).
    assert (
        probability("recovery", sex="male", select_age=40, duration=12)
        == 0.003497
    )
    # Death beyond attained 74 comes from Table 7C (p.37).
    assert (
        probability("death", sex="male", select_age=60, duration=20)
        == 0.125443
    )
    assert (
        probability("death", sex="female", select_age=50, duration=40)
        == 0.180035
    )
    assert (
        probability("death", sex="female", select_age=64, duration=46)
        == 0.577397
    )
    with pytest.raises(KeyError, match="attained age 110"):
        probability("death", sex="male", select_age=64, duration=47)


def test__di_termination_probability__recovery_is_untabulated_from_65():
    probability = tr2008.di_termination_probability
    assert (
        probability("recovery", sex="male", select_age=64, duration=1) is None
    )
    assert (
        probability("recovery", sex="male", select_age=60, duration=5) is None
    )
    assert (
        probability("recovery", sex="female", select_age=50, duration=20)
        is None
    )
    with pytest.raises(ValueError, match="select ages 16-64"):
        probability("death", sex="male", select_age=65, duration=0)
    with pytest.raises(ValueError, match="non-negative"):
        probability("death", sex="male", select_age=40, duration=-1)
    with pytest.raises(ValueError, match="cause must be"):
        probability("conversion", sex="male", select_age=40, duration=0)


def test__di_incidence_by_age__table_4_spot_values():
    # Study 118 Table 4, p.29 (printed 17).
    male_1980 = tr2008.di_incidence_by_age(1980, sex="male")
    assert tuple(male_1980.by_age) == tr2008.STUDY_118_AGE_GROUPS
    assert male_1980.by_age["15-19"] == 0.32
    assert male_1980.by_age["60-64"] == 21.42
    assert male_1980.by_age["65 or older"] == 15.18
    assert (male_1980.gross, male_1980.adjusted) == (5.04, 5.58)
    female_2004 = tr2008.di_incidence_by_age(2004, sex="female")
    assert female_2004.by_age["60-64"] == 15.39
    assert (female_2004.gross, female_2004.adjusted) == (5.63, 5.26)
    total_2000 = tr2008.di_incidence_by_age(2000)
    assert total_2000.by_age["50-54"] == 7.91
    assert total_2000.gross == total_2000.adjusted == 4.66
    with pytest.raises(KeyError, match="1980-2004"):
        tr2008.di_incidence_by_age(2005)
    with pytest.raises(ValueError, match="sex must be"):
        tr2008.di_incidence_by_age(2000, sex="both")


def test__di_terminations_and_workers__tables_5_and_6_spot_values():
    # Study 118 Table 5 p.30, Table 6 p.31.
    total_2000 = tr2008.di_terminations_by_reason(2000)
    assert total_2000.numbers == {
        "death": 168996,
        "recovery": 69483,
        "other": 10181,
        "conversion": 210067,
        "total": 458727,
    }
    assert total_2000.rates_per_1000["total"] == 88.62
    male_1980 = tr2008.di_terminations_by_reason(1980, sex="male")
    assert male_1980.numbers["death"] == 105092
    assert male_1980.rates_per_1000["death"] == 51.9
    workers = tr2008.di_workers_by_age(2004)
    assert workers.total == 6198224
    assert workers.by_age["65 or older"] == 81780
    assert sum(workers.by_age.values()) == workers.total
    assert tr2008.di_workers_by_age(1980, sex="male").total == 1925928


def test__study_118_current_pay__matches_tr2008_history_every_year():
    # Recorded observation: Study 118 Table 6 totals, in thousands, equal
    # TR2008's single-year V.C5 historical disabled workers in 1980-2004.
    observations = {
        entry["id"]: entry
        for entry in _json("transcription_check.json")["observations"]
    }
    current_pay = observations["study_118_current_pay_vs_tr2008_v_c5"][
        "disabled_workers_thousands"
    ]
    assert (current_pay["years_compared"], current_pay["equal"]) == (25, 25)
    join = observations["study_118_select_to_ultimate_join"]
    assert join["largest_difference"] == 2
    assert len(join["differing_by_more_than_one"]) == 12


def _failed_as118_checks(mutate) -> set[str]:
    study = copy.deepcopy(_json("actuarial_study_118.json"))
    mutate(study["tables"])
    return {
        check["id"]
        for check in extractor.build_as118_checks(study)
        if not check["passed"]
    }


def test__study_118_checks__pass_on_the_committed_tables():
    assert _failed_as118_checks(lambda tables: None) == set()


@pytest.mark.parametrize(
    ("mutate", "caught_by"),
    [
        (
            lambda t: t["7A"]["rows"][20]["by_duration"].__setitem__(3, 0.5),
            {
                "AS118_death_probability_vs_survival",
                "AS118_combined_equals_death_plus_recovery",
            },
        ),
        (
            lambda t: t["14B"]["rows"][5]["by_duration"].__setitem__(
                6, 0.000001
            ),
            {
                "AS118_recovery_probability_vs_survival",
                "AS118_combined_equals_death_plus_recovery",
            },
        ),
        (
            lambda t: t["7C"]["rows"][10].__setitem__("female", 0.3),
            {"AS118_old_age_death_vs_survival"},
        ),
        (
            lambda t: t["6"]["sections"]["male"][4].__setitem__(
                "age_50_54", 1
            ),
            {"AS118_table6_arithmetic"},
        ),
        (
            lambda t: t["5"]["sections"]["female"][9].__setitem__(
                "recovery_rate", 99.0
            ),
            {"AS118_table5_arithmetic"},
        ),
        (
            lambda t: t["4"]["sections"]["total"][3].__setitem__(
                "age_40_44", 9.99
            ),
            {"AS118_table4_consistency"},
        ),
    ],
)
def test__study_118_checks__catch_a_corrupted_cell(mutate, caught_by):
    # INVENTED corruption of one committed cell per case.
    assert _failed_as118_checks(mutate) == caught_by


def test__text_values__quote_is_the_full_sentence_showing_every_value():
    # Regression: quotes were cut to 400 characters, so twelve values in
    # six entries (among them the low- and high-cost DI ultimate incidence,
    # 4.2 and 6.2, and the 2027 ultimate years) were absent from the quote
    # that is their locator.
    for entry in _json("tr2008_report.json")["text_values"]:
        quote = entry["quote"]
        assert not quote.endswith("..."), entry["id"]
        printed = {
            float(token) for token in re.findall(r"\d+(?:\.\d+)?|\.\d+", quote)
        }
        for key, value in entry["values"].items():
            assert float(value) in printed, (entry["id"], key, value)


def test__text_value_check__catches_a_value_the_html_does_not_state():
    # The check reads only committed captures, not the PDF.
    report = copy.deepcopy(_json("tr2008_report.json"))
    entry = next(
        e
        for e in report["text_values"]
        if e["id"] == "di_ultimate_incidence_per_1000_exposed"
    )
    entry["values"]["intermediate"] = 5.3  # INVENTED
    checks = extractor.build_checks(
        report,
        _json("tr2008_single_year.json"),
        _json("ssa_2008_vintage.json"),
        _json("actuarial_study_118.json"),
    )
    failed = {c["id"] for c in checks["checks"] if not c["passed"]}
    assert failed == {"text_values_pdf_vs_html"}


# ---------------------------------------------------------------- rulings


def test__pending_rulings_and_gaps__are_explicit():
    parameters = {ruling.parameter for ruling in tr2008.PENDING_RULINGS}
    assert {"alternative", "post_2017", "realized / last_realized_year"} <= (
        parameters
    )
    defaults = {r.parameter: r.default for r in tr2008.PENDING_RULINGS}
    assert defaults["alternative"] == "intermediate"
    assert defaults["post_2017"] == "ultimate_cpi"
    series = " ".join(gap.series for gap in tr2008.GAPS)
    assert "Projected death probabilities" in series
    assert "DI incidence rates by age and sex" in series
    assert "DI terminations by age and sex, 2005-2008" in series
    for record in (*tr2008.PENDING_RULINGS, *tr2008.GAPS):
        assert all(
            value for value in dataclasses.asdict(record).values()
        ), record
