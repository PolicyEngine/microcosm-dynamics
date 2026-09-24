"""Track C step 1 AIME agreement script, on INVENTED data only.

Every person, career, wage index and contribution base below is INVENTED
for mechanics; none is PSID or SSA data.  The fake-engine tests check
transport, classification and recording.  The actual-engine test runs the
pinned Axiom binary on invented careers and skips when the engine or its
retained evidence is absent.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

import populace_dynamics.axiom_benefit_bridge as bridge
from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters

ROOT = Path(__file__).resolve().parents[1]


def _load_script():
    path = ROOT / "scripts" / "track_c_aime_agreement.py"
    spec = importlib.util.spec_from_file_location("track_c_aime", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Dataclasses resolve their module through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tc = _load_script()

# INVENTED parameters: a smooth wage index with cent values and a flat
# contribution base.  Not SSA's series.
INVENTED_PARAMS = SSAParameters(
    nawi={year: 1000.0 + 250.25 * (year - 1951) for year in range(1951, 2041)},
    wage_base={1951: 60000.0},
    pia_factors=(0.9, 0.32, 0.15),
    fra_months_by_birth_year=[(1900, 792)],
    early_monthly_rates=(5 / 900, 5 / 1200),
    early_first_bracket_months=36,
    pe_us_revision="INVENTED-test-parameters",
)
CUTOFF = 2010


def _career(birth_year, *, amount=30000.0, cutoff=CUTOFF):
    """INVENTED flat career from max(1968, birth + 22) through cutoff."""
    first = max(tc.PANEL_FIRST_YEAR, birth_year + 22)
    return {year: amount for year in range(first, cutoff + 1)}


def _provenance(career, kind="observed"):
    return {year: kind for year in career}


def _person(person_id, birth_year, status="none", *, career=None, **kw):
    selection = tc.select_persons(
        [(person_id, birth_year, status)], reference_year=2030
    )[0]
    career = _career(birth_year) if career is None else career
    return tc.PersonInput(selection, career, _provenance(career), **kw)


def _fake_response(request, aime, pia=None):
    outputs, selected = {}, []
    values = {bridge.AIME_OUTPUT: aime, bridge.PIA_OUTPUT: pia}
    for reference in request["outputs"]:
        name = reference.split("#", 1)[1]
        outputs[reference] = {
            "id": reference,
            "name": name,
            "dtype": "decimal",
            "unit": "USD",
            "column": {"kind": "decimal", "values": [values[reference]]},
        }
        selected.append(
            {
                "kind": "derived",
                "name": name,
                "id": reference,
                "version_index": 0,
                "effective_from": "1979-01-01",
                "effective_to": None,
            }
        )
    return {
        "schema": bridge.RESPONSE_SCHEMA,
        "engine_version": "INVENTED-fake-engine",
        "artifact_format_version": 2,
        "arithmetic": "decimal",
        "entity": "Person",
        "row_count": 1,
        "entity_ids": request["batches"][-1]["entity_ids"],
        "periods": request["periods"],
        "calculation_period": request["calculation_period"],
        "reference_period": request["output_period"],
        "output_period": request["output_period"],
        "selected_versions": selected,
        "outputs": outputs,
    }


class FakeEngine:
    """INVENTED engine: answers with a fixed AIME and records requests."""

    def __init__(self, aime="0", pia="0", code=0):
        self.aime, self.pia, self.code = aime, pia, code
        self.requests = []

    def __call__(self, argv, wire, timeout):
        request = json.loads(wire)
        self.requests.append(request)
        if self.code:
            return self.code, b"", b'{"message": "INVENTED engine failure"}'
        body = _fake_response(request, self.aime, self.pia)
        return 0, json.dumps(body).encode(), b""


@pytest.fixture
def fake_binding(tmp_path):
    files = {}
    for role, text in (
        ("engine", "#!/bin/sh\nexit 3\n"),
        (bridge.ARTIFACT_AIME_PIA, '{"invented": "aime_pia"}'),
        (bridge.ARTIFACT_AIME_ONLY, '{"invented": "aime_only"}'),
        ("module:invented.yaml", "format: invented\n"),
    ):
        path = tmp_path / role.replace(":", "_")
        path.write_text(text)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files[role] = bridge.BoundFile(role, path, digest)
    return bridge.AxiomEngineBinding(
        engine=files["engine"],
        artifacts=(
            files[bridge.ARTIFACT_AIME_PIA],
            files[bridge.ARTIFACT_AIME_ONLY],
        ),
        supporting=(files["module:invented.yaml"],),
        engine_source_commit="INVENTED-commit",
    )


def _context(name=tc.PASS_PRIMARY, *, binding=None, runner=None, **kw):
    params = kw.pop("params", INVENTED_PARAMS)
    return tc.PassContext(
        name=name,
        params=params,
        wage_index=kw.pop("wage_index", tc.track_a_wage_index(params)),
        contribution_base=tc.track_a_contribution_base(params, 1951, CUTOFF),
        binding=binding,
        cutoff_year=CUTOFF,
        anchor_wave=2011,
        runner=runner,
        **kw,
    )


def test_selection_follows_track_a_routes_and_eligibility_window():
    selections = tc.select_persons(
        [
            (1, 1916, "retired_worker"),
            (2, 1917, "retired_worker"),
            (3, 1968, "none"),
            (4, 1969, "none"),
            (5, 1950, "disabled_worker"),
            (6, 1940, "survivor"),
            (7, 1940, "other"),
            (8, 1960, "unobserved"),
            (9, 1945, "spouse"),
            (10, 1945, "unclassified"),
        ],
        reference_year=2030,
    )
    by_id = {s.person_id: s for s in selections}
    assert by_id[1].exclusion == tc.EXCLUDED_BEFORE_1979
    assert not by_id[1].selected
    assert by_id[2].route == tc.ROUTE_OPENING_RETIRED
    assert by_id[3].route == tc.ROUTE_PROJECTED
    assert by_id[4].exclusion == tc.EXCLUDED_AFTER_REFERENCE
    assert by_id[5].route == tc.ROUTE_OPENING_DI
    assert {by_id[i].route for i in (6, 7, 9, 10)} == {tc.ROUTE_OPENING_AUX}
    assert by_id[8].route == tc.ROUTE_PROJECTED
    with pytest.raises(ValueError, match="unknown opening status"):
        tc.route_for_status("invented_status")


def test_conventions_entitlement_year_and_candidate_count():
    assert tc.primary_entitlement_year(1940, 2010) == 2011
    assert tc.primary_entitlement_year(1949, 2010) == 2011
    assert tc.primary_entitlement_year(1960, 2010) == 2022
    # Elapsed years run from the later of 1950 and the year of attaining 21
    # to the year of attaining 62; the count is five fewer.
    assert tc.candidate_computation_years(1917) == 23
    assert tc.candidate_computation_years(1928) == 34
    assert tc.candidate_computation_years(1929) == 35
    assert tc.candidate_computation_years(1960) == 35


def test_oracle_arithmetic_at_35_years_is_the_oracle():
    career = _career(1930)
    career[1990] = 45191.8  # INVENTED non-dyadic amount
    assert tc.oracle_arithmetic_with_count(
        career, 1930, INVENTED_PARAMS, 35
    ) == tc.oracle_aime(career, 1930, INVENTED_PARAMS)
    assert tc.oracle_aime(career, 1930, INVENTED_PARAMS) == benefits.aime(
        career, 1930, INVENTED_PARAMS
    )
    fewer = tc.oracle_arithmetic_with_count(career, 1930, INVENTED_PARAMS, 20)
    assert fewer > tc.oracle_aime(career, 1930, INVENTED_PARAMS)


def test_transport_zero_fills_outside_the_panel_and_labels_rows():
    career = _career(1930)
    career[1975] = 90000.0  # INVENTED amount above the invented base
    career[1990] = 45191.8
    provenance = _provenance(career)
    provenance[1980] = "unknown"
    provenance[1999] = "gap_imputed"
    plan = tc.transport_rows(
        career,
        provenance,
        birth_year=1930,
        entitlement_year=2011,
        cutoff_year=CUTOFF,
        params=INVENTED_PARAMS,
    )
    years = [row.year for row in plan.rows]
    # Window starts the year after attaining 21 (1952); rows run to 2010.
    assert years == list(range(1952, 2011))
    pre = [row for row in plan.rows if row.year < 1968]
    assert len(pre) == 16
    assert all(row.synthetic and row.amount == 0 for row in pre)
    assert all(
        row.source.startswith("synthetic_caller_supplied:") for row in pre
    )
    by_year = {row.year: row for row in plan.rows}
    assert by_year[1975].amount == Decimal("60000")
    assert by_year[1975].source == "psid_career:observed"
    assert by_year[1975].synthetic is False
    assert by_year[1980].synthetic and by_year[1999].synthetic
    assert by_year[1990].amount == Decimal("45191.8")
    assert by_year[1990].amount_hex == (45191.8).hex()
    assert by_year[1990].encoding == bridge.BINARY64_SHORTEST_ROUND_TRIP
    assert plan.counts["limited_to_base"] == 1
    assert plan.counts["shortest_decimal_differs_from_binary"] == 1
    assert plan.counts["synthetic_zero_pre_panel"] == 16
    assert "synthetic_zero_post_cutoff" not in plan.counts
    assert plan.excluded_career_years == ()


def test_transport_zero_fills_after_the_cutoff_and_drops_late_years():
    plan = tc.transport_rows(
        _career(1960),
        _provenance(_career(1960)),
        birth_year=1960,
        entitlement_year=2022,
        cutoff_year=CUTOFF,
        params=INVENTED_PARAMS,
    )
    post = [row for row in plan.rows if row.year > CUTOFF]
    assert [row.year for row in post] == list(range(2011, 2022))
    assert all(row.synthetic and row.amount == 0 for row in post)
    truncated = tc.transport_rows(
        _career(1944),
        _provenance(_career(1944)),
        birth_year=1944,
        entitlement_year=2006,
        cutoff_year=CUTOFF,
        params=INVENTED_PARAMS,
    )
    assert truncated.excluded_career_years == tuple(range(2006, 2011))
    assert max(row.year for row in truncated.rows) == 2005


def test_strict_transport_is_refused_with_classified_reasons():
    record, result = tc.compare_person(
        _person(1, 1930), _context(tc.PASS_STRICT)
    )
    assert result is None
    assert record["status"] == "refused"
    assert record["refusal_classes"] == [
        "elapsed_window_years_before_the_psid_panel"
    ]
    assert record["gaps"] == {"missing_required_years": "1952-1967"}
    later, _ = tc.compare_person(_person(2, 1960), _context(tc.PASS_STRICT))
    assert later["refusal_classes"] == [
        "elapsed_window_years_after_the_cutoff"
    ]
    accepted, _ = tc.compare_person(_person(3, 1947), _context(tc.PASS_STRICT))
    assert accepted["status"] == "accepted_not_executed"
    assert "axiom_aime" not in accepted


def test_executed_records_classify_agreement(fake_binding):
    person = _person(1, 1935)
    oracle = tc.oracle_aime(person.career, 1935, INVENTED_PARAMS)
    engine = FakeEngine(aime=str(oracle))
    record, result = tc.compare_person(
        person, _context(binding=fake_binding, runner=engine)
    )
    assert record["status"] == "executed"
    assert record["exact_match"] is True
    assert record["difference"] == "0"
    assert record["attribution"] == tc.ATTR_EXACT
    assert record["entitlement_year_sent"] == 2011
    assert record["request_sha256"] == result.prepared.request_sha256
    request = engine.requests[0]
    assert request["outputs"] == [bridge.AIME_OUTPUT]
    # Window 1957-2010: eleven zero years before 1968, then the career.
    assert len(request["batches"]) == 2011 - 1957

    early = _person(2, 1920)
    count = tc.candidate_computation_years(1920)
    at_count = tc.oracle_arithmetic_with_count(
        early.career, 1920, INVENTED_PARAMS, count
    )
    record, _ = tc.compare_person(
        early,
        _context(binding=fake_binding, runner=FakeEngine(str(at_count))),
    )
    assert record["attribution"] == tc.ATTR_COUNT
    assert Decimal(record["difference"]) == at_count - (
        record["track_a_oracle_aime"]
    )

    record, _ = tc.compare_person(
        person,
        _context(binding=fake_binding, runner=FakeEngine(str(oracle + 1))),
    )
    assert record["attribution"] == tc.ATTR_UNEXPLAINED
    assert record["difference"] == "1"


def test_refusals_and_engine_failures_are_recorded(fake_binding):
    short_index = bridge.AnnualSeries.from_mapping(
        "INVENTED wage index missing 1990",
        {
            year: tc._float_text(value)
            for year, value in INVENTED_PARAMS.nawi.items()
            if year != 1990
        },
    )
    record, _ = tc.compare_person(
        _person(1, 1935),
        _context(
            binding=fake_binding, runner=FakeEngine(), wage_index=short_index
        ),
    )
    assert record["status"] == "refused"
    assert record["gaps"] == {"missing_wage_index_years": "1990"}
    assert record["refusal_classes"] == ["missing_wage_index_years"]
    failed, result = tc.compare_person(
        _person(2, 1935),
        _context(binding=fake_binding, runner=FakeEngine(code=2)),
    )
    assert result is None
    assert failed["status"] == "failed"
    assert "INVENTED engine failure" in failed["reasons"][0]


def test_diagnostic_pass_compares_the_same_truncated_years(fake_binding):
    career = _career(1944)
    career[2008] = 200000.0  # INVENTED late peak after entitlement
    person = _person(1, 1944, "retired_worker", career=career)
    person = tc.PersonInput(
        person.selection,
        person.career,
        person.provenance,
        opening_entitlement_year=2006,
    )
    truncated = {y: v for y, v in career.items() if y < 2006}
    oracle_truncated = tc.oracle_aime(truncated, 1944, INVENTED_PARAMS)
    record, _ = tc.compare_person(
        person,
        _context(
            tc.PASS_DIAGNOSTIC,
            binding=fake_binding,
            runner=FakeEngine(str(oracle_truncated)),
        ),
    )
    assert record["entitlement_year_sent"] == 2006
    assert record["oracle_aime_on_sent_years"] == oracle_truncated
    assert record["truncation_effect_on_oracle"] == oracle_truncated - (
        tc.oracle_aime(career, 1944, INVENTED_PARAMS)
    )
    assert record["truncation_effect_on_oracle"] < 0
    assert record["career_years_not_sent"] == "2006-2010"
    assert record["exact_match"] is True


def test_pia_formula_check_records_the_1964_cohort(fake_binding):
    person = _person(1, 1964)
    oracle = tc.oracle_aime(person.career, 1964, INVENTED_PARAMS)
    pia = benefits.pia(float(oracle), 2026, INVENTED_PARAMS)
    engine = FakeEngine(aime=str(oracle), pia=tc._float_text(pia))
    record, result = tc.compare_person(
        person,
        _context(
            binding=fake_binding,
            runner=engine,
            pia_check_params=INVENTED_PARAMS,
        ),
    )
    assert engine.requests[0]["outputs"] == [
        bridge.AIME_OUTPUT,
        bridge.PIA_OUTPUT,
    ]
    assert record["artifact_role"] == bridge.ARTIFACT_AIME_PIA
    assert record["pia_formula_difference"] == "0"
    assert record["pia_status"] == "computed_by_2026_cohort_candidate"


def test_run_pass_and_summaries(fake_binding):
    people = [_person(i, 1930 + i) for i in range(1, 7)]
    answers = {
        p.selection.person_id: tc.oracle_aime(
            p.career, p.selection.birth_year, INVENTED_PARAMS
        )
        for p in people
    }

    def by_id(argv, wire, timeout):
        request = json.loads(wire)
        entity = request["batches"][0]["entity_ids"][0]
        pid = int(entity.rsplit("-", 1)[1])
        aime = str(answers[pid] + (2 if pid == 3 else 0))
        return 0, json.dumps(_fake_response(request, aime)).encode(), b""

    records = tc.run_pass(
        people, _context(binding=fake_binding, runner=by_id), workers=3
    )
    assert [r["person_id"] for r in records] == list(range(1, 7))
    summary = tc.summarize_pass(records)
    overall = summary["overall"]
    assert overall["executed"] == 6
    assert overall["exact_matches"] == 5
    assert overall["exact_match_share_of_executed"] == pytest.approx(5 / 6)
    assert overall["difference_counts"] == {"0": 5, "2": 1}
    assert overall["nonzero_differences"]["count"] == 1
    assert overall["attribution"] == {
        tc.ATTR_EXACT: 5,
        tc.ATTR_UNEXPLAINED: 1,
    }
    assert set(summary["by_route"]) == {tc.ROUTE_PROJECTED}
    assert overall["rows"]["sent"] == sum(r["rows"]["sent"] for r in records)
    assert overall["rows"]["synthetic_zero_pre_panel"] == sum(
        r["rows"]["synthetic_zero_pre_panel"] for r in records
    )
    assert summary["by_computation_year_count"] == {
        "35": {
            "persons": 6,
            "birth_years": "1931-1936",
            "executed": 6,
            "exact_matches": 5,
            "attribution": {tc.ATTR_EXACT: 5, tc.ATTR_UNEXPLAINED: 1},
            "max_difference": "2",
        }
    }


def test_difference_bins_are_half_open_and_exhaustive():
    counts = {"-3": 1, "0": 4, "1": 2, "9": 1, "10": 1, "499": 1, "500": 3}
    bins = tc.difference_bins(counts)
    assert list(bins) == [label for label, _, _ in tc.DIFFERENCE_BINS]
    assert bins["below 0"] == 1
    assert bins["0"] == 4
    assert bins["1 to 9"] == 3
    assert bins["10 to 49"] == 1
    assert bins["200 to 499"] == 1
    assert bins["500 and above"] == 3
    assert sum(bins.values()) == sum(counts.values())


def test_track_a_artifact_binding_compares_cohort_and_parameters():
    # INVENTED artifact fragment and cohort diagnostics.
    diagnostics = {"members": 3, "a3_spec": {"m4_waves": (2011,)}}
    source = {"kind": "psid_files", "content_sha256": "INVENTED"}
    artifact = {
        "ssa_parameters_revision": "INVENTED+tr2008",
        "cohorts": {
            "2011": {
                "members": 3,
                "a3_spec": {"m4_waves": [2011]},
                "source_provenance": dict(source),
            }
        },
    }
    checks = tc.track_a_artifact_binding(
        artifact,
        anchor_wave=2011,
        diagnostics=diagnostics,
        source_provenance=source,
        parameters_revision="INVENTED+tr2008",
    )
    assert all(checks.values())
    changed = tc.track_a_artifact_binding(
        artifact,
        anchor_wave=2011,
        diagnostics={**diagnostics, "members": 4},
        source_provenance=source,
        parameters_revision="INVENTED+other",
    )
    assert changed == {
        "ssa_parameters_revision_equal": False,
        "cohort_diagnostics_equal": False,
        "cohort_source_provenance_equal": True,
    }


def test_decimal_and_float_text_are_plain():
    assert tc._decimal_str(Decimal("5825.00")) == "5825"
    assert tc._decimal_str(Decimal("-0.00")) == "0"
    assert tc._decimal_str(Decimal("100")) == "100"
    assert tc._decimal_str(Decimal("2609.80")) == "2609.8"
    assert tc._float_text(77383.0) == "77383"
    assert tc._float_text(2799.16) == "2799.16"
    series = tc.track_a_wage_index(INVENTED_PARAMS)
    assert series.get(1951) == "1000"
    assert series.source_sha256 is not None


def _invented_result(fake_binding):
    people = [_person(1, 1935), _person(2, 1920, "retired_worker")]
    records = tc.run_pass(
        people,
        _context(binding=fake_binding, runner=FakeEngine("100")),
    )
    strict = tc.run_pass(people, _context(tc.PASS_STRICT))
    return {
        "partial": True,
        "cohort": {
            "anchor_wave": 2011,
            "cutoff_year": CUTOFF,
            "members": 2,
            "psid_files_bundle_sha256": "INVENTED",
            "a3_content_sha256": "INVENTED",
            "track_a_seal": "INVENTED",
        },
        "selection": {
            "selected": 2,
            "eligibility_window": "1979-2030",
            "exclusions": {},
            "exclusion_definitions": dict(tc.EXCLUSIONS),
            "routes": {tc.ROUTE_PROJECTED: 1, tc.ROUTE_OPENING_RETIRED: 1},
        },
        "declarations": {"covered earnings": "INVENTED declaration"},
        "parameters": {
            "track_a_revision": "INVENTED",
            "wage_index": {"source_sha256": "INVENTED", "years": "1951"},
            "contribution_base": {"source_sha256": "INVENTED"},
        },
        "passes": {
            tc.PASS_PRIMARY: {"summary": tc.summarize_pass(records)},
            tc.PASS_STRICT: {"summary": tc.summarize_pass(strict)},
        },
        "pia_check": {
            "persons": 0,
            "agree": 0,
            "difference_counts": {},
            "published_bend_points_2026": "INVENTED",
            "track_a_bend_points_2026": "INVENTED",
            "check_params_revision": "INVENTED",
        },
        "not_compared": ["INVENTED item"],
        "executions": {
            "examples_per_class": 3,
            "max_unexplained_per_pass": 500,
            "persons_written": 0,
            "written_by_pass_and_attribution": {},
        },
        "provenance": {
            "engine_binding": fake_binding.document(),
            "engine_versions": ["INVENTED-fake-engine"],
            "git": {"head": "INVENTED", "clean": False},
            "source_sha256": {
                "scripts/track_c_aime_agreement.py": "INVENTED",
                "src/populace_dynamics/axiom_benefit_bridge.py": "INVENTED",
            },
        },
    }


def test_render_labels_candidates_and_computes_no_age_profile(
    fake_binding, tmp_path
):
    result = _invented_result(fake_binding)
    text = tc.render_results(result)
    assert "PARTIAL SMOKE RUN" in text
    assert "candidates are unaccepted" in text
    assert "not** the COLA statistic" in text
    for group in ("50-61", "62-64", "65-69", "70-79", "80+"):
        assert group not in text
    assert "at most 500 per pass" in text
    assert "## Result" in text
    assert "| 1 to 9 |" in text
    assert "Rows sent to the engine" in text
    # Person 2 (born 1920) has 26 candidate computation years.
    assert "| 26 | 1920-1920 | 1 |" in text
    assert "derives them from SSA's published 2024 AWI" in text
    (tmp_path / "result.json").write_text(json.dumps(result))
    assert tc.main(["--render-only", str(tmp_path)]) == 0
    assert (tmp_path / "RESULTS.md").read_text() == text


def test_actual_engine_agrees_with_the_oracle_on_invented_careers():
    binding = bridge.reviewed_case_a_binding()
    missing = [str(path) for path in binding.missing_files()]
    if missing:
        pytest.skip(
            "actual Axiom engine or evidence absent: " + ", ".join(missing)
        )
    career = _career(1935)
    career[1990] = 45191.8  # INVENTED non-dyadic amount
    career[1975] = 90000.0  # INVENTED amount above the invented base
    modern = tc.PersonInput(
        tc.select_persons([(1, 1935, "none")], reference_year=2030)[0],
        career,
        _provenance(career),
    )
    record, result = tc.compare_person(modern, _context(binding=binding))
    assert record["status"] == "executed"
    assert result.engine_version == "0.2.2"
    assert record["exact_match"] is True
    assert record["attribution"] == tc.ATTR_EXACT
    early, _ = tc.compare_person(_person(2, 1920), _context(binding=binding))
    assert early["candidate_computation_years"] == 26
    assert early["attribution"] == tc.ATTR_COUNT
    assert Decimal(early["axiom_aime"]) > early["track_a_oracle_aime"]
