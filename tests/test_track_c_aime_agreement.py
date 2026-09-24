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
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a.benefits import TRACK_A_COMPUTATION_YEARS
from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.ss.statutory_aime import ComputationYears

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
STATUTORY = ComputationYears.STATUTORY
LEGACY = ComputationYears.LEGACY_FIXED_35

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


def _context(
    name=tc.PASS_PRIMARY,
    *,
    binding=None,
    runner=None,
    oracle=STATUTORY,
    **kw,
):
    params = kw.pop("params", INVENTED_PARAMS)
    return tc.PassContext(
        name=name,
        params=params,
        wage_index=kw.pop("wage_index", tc.track_a_wage_index(params)),
        contribution_base=tc.track_a_contribution_base(params, 1951, CUTOFF),
        binding=binding,
        cutoff_year=CUTOFF,
        anchor_wave=2011,
        oracle_convention=oracle,
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


def test_the_candidate_count_is_the_statutory_oracle_s_count():
    # The report says no disagreement can be attributed to the count under
    # the statutory oracle: the two counts agree for every birth year the
    # statutory oracle accepts (attaining 62 in 1975 or later).
    for birth in range(1913, 2001):
        assert tc.candidate_computation_years(
            birth
        ) == tc.oracle_computation_year_count(birth, STATUTORY), birth
    assert tc.oracle_computation_year_count(1913, LEGACY) == 35


def test_oracle_arithmetic_at_the_oracle_s_count_is_the_oracle():
    career = _career(1930)
    career[1990] = 45191.8  # INVENTED non-dyadic amount
    legacy = tc.oracle_aime(career, 1930, INVENTED_PARAMS, convention=LEGACY)
    assert (
        tc.oracle_arithmetic_with_count(career, 1930, INVENTED_PARAMS, 35)
        == legacy
    )
    assert legacy == benefits.aime(career, 1930, INVENTED_PARAMS)
    # Born 1930: 35 statutory years, so the two oracles agree.
    assert tc.oracle_computation_year_count(1930, STATUTORY) == 35
    assert (
        tc.oracle_aime(career, 1930, INVENTED_PARAMS, convention=STATUTORY)
        == legacy
    )
    fewer = tc.oracle_arithmetic_with_count(career, 1930, INVENTED_PARAMS, 20)
    assert fewer > legacy
    # INVENTED career of a person born 1920: 26 statutory years.  The
    # statutory oracle is the arithmetic at that count; the legacy one at 35.
    early = _career(1920)
    assert tc.oracle_computation_year_count(1920, STATUTORY) == 26
    assert tc.oracle_computation_year_count(1920, LEGACY) == 35
    statutory = tc.oracle_aime(
        early, 1920, INVENTED_PARAMS, convention=STATUTORY
    )
    assert statutory == tc.oracle_arithmetic_with_count(
        early, 1920, INVENTED_PARAMS, 26
    )
    assert tc.oracle_aime(
        early, 1920, INVENTED_PARAMS, convention=LEGACY
    ) == benefits.aime(early, 1920, INVENTED_PARAMS)
    assert statutory > benefits.aime(early, 1920, INVENTED_PARAMS)


def test_the_oracle_choice_defaults_to_statutory_and_is_named():
    parser = tc.build_parser()
    assert parser.parse_args([]).oracle_computation_years == "statutory"
    assert tc.DEFAULT_ORACLE == "statutory"
    legacy_args = ["--oracle-computation-years", "legacy_fixed_35"]
    assert (
        parser.parse_args(legacy_args).oracle_computation_years
        == "legacy_fixed_35"
    )
    with pytest.raises(SystemExit):
        parser.parse_args(["--oracle-computation-years", "fixed_35"])
    assert tc.oracle_convention("statutory") is STATUTORY
    assert tc.oracle_convention("legacy_fixed_35") is LEGACY
    assert tc.oracle_convention(LEGACY) is LEGACY
    with pytest.raises(ValueError, match="unknown oracle computation years"):
        tc.oracle_convention("statutory_415_b_2")
    assert tc.oracle_choice(STATUTORY) == "statutory"
    assert tc.oracle_choice(LEGACY) == "legacy_fixed_35"
    for convention, phrase in (
        (STATUTORY, "statutory computation years (42 USC 415(b)(2)"),
        (LEGACY, "Track A's legacy fixed 35 computation years"),
    ):
        assert phrase in tc.header_for(convention)
        assert "oracle: " + tc.ORACLE_NAMES[convention] in tc.labels_for(
            convention
        )
        document = tc.oracle_document(convention)
        assert document["computation_years"] == convention.value
        assert document["choice"] == tc.oracle_choice(convention)
        assert document["is_track_a_convention"] is (convention is LEGACY)
        assert document["track_a_computation_years"] == LEGACY.value
        assert f"ComputationYears.{convention.name}" in document["call"]
    # Only the non-Track-A oracle adds a not-compared item about Track A.
    assert len(tc.not_compared(STATUTORY)) == len(tc.not_compared(LEGACY)) + 1
    assert "track_a_oracle_aime" in tc.not_compared(STATUTORY)[-1]


def test_track_a_s_convention_is_still_the_legacy_fixed_35():
    # The report names Track A's AIME as the fixed-35 one under either
    # choice, so a change of Track A's convention stops the script.
    assert TRACK_A_COMPUTATION_YEARS is LEGACY
    assert tc.LEGACY_COMPUTATION_YEARS == 35
    tc.require_track_a_convention()
    tc.require_track_a_convention(LEGACY)
    with pytest.raises(SystemExit, match="statutory_415_b_2"):
        tc.require_track_a_convention(STATUTORY)


@pytest.mark.parametrize(
    ("oracle", "checked"),
    [
        (STATUTORY, [STATUTORY.value, LEGACY.value]),
        (LEGACY, [LEGACY.value]),
    ],
)
def test_oracle_pia_check_follows_the_chosen_oracle(
    monkeypatch, oracle, checked
):
    # INVENTED people born 1925 and 1960.  The check calls
    # eligibility_pia_for_clock with the chosen convention and with Track
    # A's, as Track A's assembly does.
    people = [_person(1, 1925), _person(2, 1960)]
    document = tc.check_oracle_pia(people, INVENTED_PARAMS, oracle)
    assert document["persons"] == 2
    assert document["conventions_checked"] == checked
    # The two conventions give the 1925 person different PIAs, so each
    # check is a real constraint.
    early = people[0]
    pias = {
        convention: sb.eligibility_pia_for_clock(
            sb.WorkerClock.at_age_62(1925),
            history=early.career,
            birth_year=1925,
            params=INVENTED_PARAMS,
            computation_years=convention,
        )
        for convention in (STATUTORY, LEGACY)
    }
    assert pias[STATUTORY] != pias[LEGACY]
    assert pias[LEGACY] == benefits.pia(
        tc.oracle_aime(early.career, 1925, INVENTED_PARAMS, convention=LEGACY),
        1987,
        INVENTED_PARAMS,
    )
    # A PIA that does not rest on the recorded oracle AIME is refused.
    original = tc.oracle_aime
    monkeypatch.setattr(
        tc,
        "oracle_aime",
        lambda career, birth, params, *, convention: original(
            career, birth, params, convention=convention
        )
        + 100,
    )
    with pytest.raises(ValueError, match="1: PIA mismatch"):
        tc.check_oracle_pia(people, INVENTED_PARAMS, oracle)


def test_oracle_pia_check_needs_the_computation_years_pin(monkeypatch):
    # A PIA function that ignores computation_years (always its statutory
    # default) must fail the Track A (legacy) check for someone born 1925.
    original = sb.eligibility_pia_for_clock

    def unpinned(clock, *, history, birth_year, params, computation_years):
        return original(
            clock, history=history, birth_year=birth_year, params=params
        )

    monkeypatch.setattr(tc.sb, "eligibility_pia_for_clock", unpinned)
    people = [_person(1, 1925)]
    with pytest.raises(ValueError, match="1: PIA mismatch \\(legacy"):
        tc.check_oracle_pia(people, INVENTED_PARAMS, STATUTORY)
    with pytest.raises(ValueError, match="1: PIA mismatch \\(legacy"):
        tc.check_oracle_pia(people, INVENTED_PARAMS, LEGACY)
    # Born 1960: 35 years either way, so the unpinned call passes.
    tc.check_oracle_pia([_person(2, 1960)], INVENTED_PARAMS, LEGACY)


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


@pytest.mark.parametrize("oracle", [STATUTORY, LEGACY])
def test_executed_records_classify_agreement(fake_binding, oracle):
    person = _person(1, 1935)
    aime = tc.oracle_aime(
        person.career, 1935, INVENTED_PARAMS, convention=oracle
    )
    engine = FakeEngine(aime=str(aime))
    record, result = tc.compare_person(
        person, _context(binding=fake_binding, runner=engine, oracle=oracle)
    )
    assert record["status"] == "executed"
    assert record["exact_match"] is True
    assert record["difference"] == "0"
    assert record["attribution"] == tc.ATTR_EXACT
    assert record["entitlement_year_sent"] == 2011
    assert record["request_sha256"] == result.prepared.request_sha256
    # Born 1935: 35 years under either oracle, and Track A's AIME is the
    # oracle's.
    assert record["oracle_computation_years"] == 35
    assert record["oracle_aime"] == record["track_a_oracle_aime"] == aime
    request = engine.requests[0]
    assert request["outputs"] == [bridge.AIME_OUTPUT]
    # Window 1957-2010: eleven zero years before 1968, then the career.
    assert len(request["batches"]) == 2011 - 1957

    record, _ = tc.compare_person(
        person,
        _context(
            binding=fake_binding,
            runner=FakeEngine(str(aime + 1)),
            oracle=oracle,
        ),
    )
    assert record["attribution"] == tc.ATTR_UNEXPLAINED
    assert record["difference"] == "1"


def test_the_legacy_oracle_attributes_the_count_the_statutory_one_uses(
    fake_binding,
):
    # INVENTED career of a person born 1920 (26 candidate computation
    # years); the engine answers with the oracle arithmetic at 26 years.
    early = _person(2, 1920)
    count = tc.candidate_computation_years(1920)
    at_count = tc.oracle_arithmetic_with_count(
        early.career, 1920, INVENTED_PARAMS, count
    )
    legacy, _ = tc.compare_person(
        early,
        _context(
            binding=fake_binding,
            runner=FakeEngine(str(at_count)),
            oracle=LEGACY,
        ),
    )
    assert legacy["oracle_computation_years"] == 35
    assert legacy["oracle_aime"] == legacy["track_a_oracle_aime"]
    assert legacy["attribution"] == tc.ATTR_COUNT
    assert Decimal(legacy["difference"]) == at_count - legacy["oracle_aime"]
    assert Decimal(legacy["difference"]) > 0
    statutory, _ = tc.compare_person(
        early,
        _context(
            binding=fake_binding,
            runner=FakeEngine(str(at_count)),
            oracle=STATUTORY,
        ),
    )
    assert statutory["oracle_computation_years"] == count == 26
    assert statutory["oracle_aime"] == at_count
    assert statutory["track_a_oracle_aime"] == legacy["oracle_aime"]
    assert statutory["attribution"] == tc.ATTR_EXACT
    # Under the statutory oracle the count explains nothing: a different
    # engine answer is unexplained even if it were the legacy arithmetic.
    other, _ = tc.compare_person(
        early,
        _context(
            binding=fake_binding,
            runner=FakeEngine(str(legacy["oracle_aime"])),
            oracle=STATUTORY,
        ),
    )
    assert other["attribution"] == tc.ATTR_UNEXPLAINED


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
    oracle_truncated = tc.oracle_aime(
        truncated, 1944, INVENTED_PARAMS, convention=STATUTORY
    )
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
        tc.oracle_aime(career, 1944, INVENTED_PARAMS, convention=STATUTORY)
    )
    assert record["truncation_effect_on_oracle"] < 0
    assert record["career_years_not_sent"] == "2006-2010"
    assert record["exact_match"] is True


def test_pia_formula_check_records_the_1964_cohort(fake_binding):
    person = _person(1, 1964)
    oracle = tc.oracle_aime(
        person.career, 1964, INVENTED_PARAMS, convention=STATUTORY
    )
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
            p.career,
            p.selection.birth_year,
            INVENTED_PARAMS,
            convention=STATUTORY,
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
    # Born 1931-1936: 35 years, so the statutory oracle is Track A's.
    assert overall["oracle_aime_differs_from_track_a"] == 0
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


# INVENTED artifact fragment and cohort diagnostics, in the shape of
# runs/replication_urban2010_cola_v1.json's cohorts and of
# cola_track_a.opening's diagnostics.
_SOURCE = {"kind": "psid_files", "content_sha256": "INVENTED"}
_RECORDED = {
    "members": 3,
    "a3_spec": {"m4_waves": [2011]},
    "opening_stock_clock_rules": {
        "a3_receipt_start": 7,
        "linked_worker_birth_plus_62": 4,
        "own_birth_plus_62": 10,
    },
    "opening_stock_entitlement_clamped": 5,
}
_ADDITIVE_KEY = "opening_stock_entitlement_clamped_by_clock_rule"
#: INVENTED breakdown that sums to the recorded total (5) and fits within
#: the recorded clock-rule counts (4 and 10).
_ADDITIVE_VALUE = {"linked_worker_birth_plus_62": 2, "own_birth_plus_62": 3}
_ALL_CHECKS_TRUE = {
    "ssa_parameters_revision_equal": True,
    "cohort_diagnostics_equal_on_recorded_keys": True,
    "additive_diagnostic_keys_known": True,
    "additive_breakdowns_sum_to_recorded_totals": True,
    "additive_breakdowns_within_recorded_categories": True,
    "cohort_source_provenance_equal": True,
}


def _artifact(recorded=None):
    return {
        "ssa_parameters_revision": "INVENTED+tr2008",
        "cohorts": {
            "2011": {
                **(_RECORDED if recorded is None else recorded),
                "source_provenance": dict(_SOURCE),
            }
        },
    }


def _binding(diagnostics, *, artifact=None, revision="INVENTED+tr2008"):
    return tc.track_a_artifact_binding(
        _artifact() if artifact is None else artifact,
        anchor_wave=2011,
        diagnostics=diagnostics,
        source_provenance=_SOURCE,
        parameters_revision=revision,
    )


def _failed(binding):
    return sorted(k for k, ok in binding["checks"].items() if not ok)


def test_track_a_artifact_binding_compares_cohort_and_parameters():
    diagnostics = {**_RECORDED, "a3_spec": {"m4_waves": (2011,)}}
    binding = _binding(diagnostics)
    assert binding["checks"] == _ALL_CHECKS_TRUE
    assert binding["recorded_diagnostic_keys"] == sorted(_RECORDED)
    assert binding["additive_diagnostic_keys"] == {}
    assert binding["unknown_additive_diagnostic_keys"] == []
    changed = _binding(
        {**diagnostics, "members": 4}, revision="INVENTED+other"
    )
    assert changed["checks"] == {
        **_ALL_CHECKS_TRUE,
        "ssa_parameters_revision_equal": False,
        "cohort_diagnostics_equal_on_recorded_keys": False,
    }
    assert changed["recorded_keys_changed"] == {
        "members": {"recorded": 3, "fresh": 4}
    }
    missing = _binding(
        {k: v for k, v in diagnostics.items() if k != "members"}
    )
    assert _failed(missing) == ["cohort_diagnostics_equal_on_recorded_keys"]
    assert missing["recorded_keys_missing"] == ["members"]


def test_the_reviewed_additive_diagnostic_is_recorded_not_refused():
    # Regression: #454 (bfe9fa3e) added
    # opening_stock_entitlement_clamped_by_clock_rule to the cohort
    # diagnostics after the Track A artifact was written, and the
    # whole-dict comparison stopped every real run before any engine call
    # (cohort_diagnostics_equal: False).
    assert tc.KNOWN_ADDITIVE_DIAGNOSTICS == {
        _ADDITIVE_KEY: {
            "added_by": "bfe9fa3e",
            "total": "opening_stock_entitlement_clamped",
            "categories": "opening_stock_clock_rules",
        }
    }
    fresh = {**_RECORDED, _ADDITIVE_KEY: dict(_ADDITIVE_VALUE)}
    recorded = dict(_artifact()["cohorts"]["2011"])
    recorded.pop("source_provenance")
    assert tc._json_normal(recorded) != tc._json_normal(fresh)
    binding = _binding(fresh)
    assert binding["checks"] == _ALL_CHECKS_TRUE
    assert binding["additive_diagnostic_keys"] == {
        _ADDITIVE_KEY: _ADDITIVE_VALUE
    }
    assert binding["additive_breakdowns"] == {
        _ADDITIVE_KEY: {
            "added_by": "bfe9fa3e",
            "total_key": "opening_stock_entitlement_clamped",
            "recorded_total": 5,
            "sum": 5,
            "sums_to_recorded_total": True,
            "categories_key": "opening_stock_clock_rules",
            "within_recorded_categories": True,
        }
    }
    # A breakdown that does not sum to the recorded total is refused.
    off = _binding({**fresh, _ADDITIVE_KEY: {"own_birth_plus_62": 4}})
    assert _failed(off) == ["additive_breakdowns_sum_to_recorded_totals"]
    not_counts = _binding({**fresh, _ADDITIVE_KEY: ["own_birth_plus_62"]})
    assert "additive_breakdowns_sum_to_recorded_totals" in _failed(not_counts)
    # Changing a recorded key is still refused alongside an additive one.
    changed = _binding({**fresh, "opening_stock_entitlement_clamped": 6})
    assert "cohort_diagnostics_equal_on_recorded_keys" in _failed(changed)


@pytest.mark.parametrize(
    "breakdown",
    [
        # Sums to 5 but counts 5 under a rule the artifact counts 4 times.
        {"linked_worker_birth_plus_62": 5},
        # Sums to 5 but names a rule the artifact never counts.
        {"invented_rule": 2, "own_birth_plus_62": 3},
        # Sums to 5 only through a negative count.
        {"own_birth_plus_62": 6, "linked_worker_birth_plus_62": -1},
    ],
)
def test_an_additive_breakdown_must_fit_the_recorded_categories(breakdown):
    # Regression: the 71c94743 check accepted each of these (it tested the
    # sum only).
    binding = _binding({**_RECORDED, _ADDITIVE_KEY: breakdown})
    assert "additive_breakdowns_within_recorded_categories" in (
        _failed(binding)
    )
    assert not all(binding["checks"].values())


@pytest.mark.parametrize(
    "extra",
    [
        # Not a breakdown of anything recorded.
        {"invented_new_counter": 7},
        # Named like a breakdown of a recorded total and summing to it, but
        # never reviewed.
        {"opening_stock_entitlement_clamped_by_invented_rule": {"a": 5}},
    ],
)
def test_an_unreviewed_diagnostic_the_artifact_lacks_is_refused(extra):
    # Regression: the whole-dict comparison refused any new diagnostic; the
    # 71c94743 check accepted both of these (the first as "recorded only",
    # the second through its <total>_by_<rule> name).  Only the reviewed
    # KNOWN_ADDITIVE_DIAGNOSTICS may be absent from the artifact.
    fresh = {**_RECORDED, _ADDITIVE_KEY: dict(_ADDITIVE_VALUE), **extra}
    binding = _binding(fresh)
    assert _failed(binding) == ["additive_diagnostic_keys_known"]
    assert binding["unknown_additive_diagnostic_keys"] == sorted(extra)
    assert binding["additive_breakdowns"][next(iter(extra))] is None


def test_require_track_a_artifact_refuses_and_records(tmp_path):
    fresh = {**_RECORDED, _ADDITIVE_KEY: dict(_ADDITIVE_VALUE)}
    artifact_bytes = json.dumps(_artifact()).encode()
    kwargs = dict(
        path="INVENTED/artifact.json",
        anchor_wave=2011,
        source_provenance=_SOURCE,
        parameters_revision="INVENTED+tr2008",
    )
    document = tc.require_track_a_artifact(
        artifact_bytes, diagnostics=fresh, **kwargs
    )
    assert document["path"] == "INVENTED/artifact.json"
    assert document["sha256"] == hashlib.sha256(artifact_bytes).hexdigest()
    assert document["additive_diagnostic_keys"] == {
        _ADDITIVE_KEY: _ADDITIVE_VALUE
    }
    text = tc._artifact_binding_text(document)
    assert "4 keys" in text
    assert f"`{_ADDITIVE_KEY}`" in text
    assert (
        "(added in `bfe9fa3e`; sum 5, recorded "
        "`opening_stock_entitlement_clamped` 5; within recorded "
        "`opening_stock_clock_rules`: yes)"
    ) in text
    assert "an unlisted diagnostic refuses the run" in text
    plain = tc._artifact_binding_text(
        tc.require_track_a_artifact(
            artifact_bytes, diagnostics=dict(_RECORDED), **kwargs
        )
    )
    assert "records no other diagnostic" in plain
    with pytest.raises(SystemExit) as refused:
        tc.require_track_a_artifact(
            artifact_bytes, diagnostics={**fresh, "members": 4}, **kwargs
        )
    message = str(refused.value)
    assert "INVENTED/artifact.json" in message
    assert "cohort_diagnostics_equal_on_recorded_keys" in message
    assert "'members': {'recorded': 3, 'fresh': 4}" in message
    with pytest.raises(SystemExit) as unknown:
        tc.require_track_a_artifact(
            artifact_bytes,
            diagnostics={**fresh, "invented_new_counter": 7},
            **kwargs,
        )
    message = str(unknown.value)
    assert "additive_diagnostic_keys_known" in message
    assert "KNOWN_ADDITIVE_DIAGNOSTICS ['invented_new_counter']" in message


def test_a_run_requires_an_output_dir(monkeypatch):
    # Regression: the default --output-dir named the 2026-09-23 evidence
    # directory, so a run without the flag was aimed at an earlier run's
    # directory.  The check precedes every git, engine and data step.
    assert tc.build_parser().parse_args([]).output_dir is None

    def no_git(*args):
        raise AssertionError("reached git before refusing")

    monkeypatch.setattr(tc, "_git", no_git)
    with pytest.raises(SystemExit, match="--output-dir is required"):
        tc.main([])


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


def _invented_result(fake_binding, oracle=STATUTORY):
    people = [_person(1, 1935), _person(2, 1920, "retired_worker")]
    records = tc.run_pass(
        people,
        _context(
            binding=fake_binding, runner=FakeEngine("100"), oracle=oracle
        ),
    )
    strict = tc.run_pass(people, _context(tc.PASS_STRICT, oracle=oracle))
    return {
        "schema_version": tc.SCHEMA_VERSION,
        "header": tc.header_for(oracle),
        "labels": list(tc.labels_for(oracle)),
        "oracle": tc.oracle_document(oracle),
        "partial": True,
        "cohort": {
            "anchor_wave": 2011,
            "cutoff_year": CUTOFF,
            "members": 2,
            "psid_files_bundle_sha256": "INVENTED",
            "a3_content_sha256": "INVENTED",
            "track_a_seal": "INVENTED",
            "track_a_artifact": {
                "path": "INVENTED/artifact.json",
                "sha256": "INVENTED",
                **_binding({**_RECORDED, _ADDITIVE_KEY: _ADDITIVE_VALUE}),
            },
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
        "oracle_pia_consistency": {
            "persons": 2,
            "conventions_checked": list(
                dict.fromkeys((oracle.value, LEGACY.value))
            ),
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


@pytest.mark.parametrize("oracle", [STATUTORY, LEGACY])
def test_render_labels_candidates_and_computes_no_age_profile(
    fake_binding, tmp_path, oracle
):
    result = _invented_result(fake_binding, oracle)
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
    # The artifact binding names the additive diagnostic.
    assert f"`{_ADDITIVE_KEY}`" in text
    (tmp_path / "result.json").write_text(json.dumps(result))
    assert tc.main(["--render-only", str(tmp_path)]) == 0
    assert (tmp_path / "RESULTS.md").read_text() == text


def test_render_names_the_oracle_compared_against(fake_binding):
    statutory = tc.render_results(_invented_result(fake_binding, STATUTORY))
    legacy = tc.render_results(_invented_result(fake_binding, LEGACY))
    title = "# Track C step 1: AIME agreement, Axiom engine vs Python oracle"
    assert statutory.splitlines()[0] == title + (
        " (statutory computation years)"
    )
    assert legacy.splitlines()[0] == title + (
        " (legacy fixed-35 computation years)"
    )
    for text, convention in ((statutory, STATUTORY), (legacy, LEGACY)):
        name = tc.ORACLE_NAMES[convention]
        assert f"**Oracle: {name}**" in text
        assert f"Primary pass, oracle with {name}:" in text
        assert (
            f"`--oracle-computation-years {tc.oracle_choice(convention)}`"
            in text
        )
    assert "computation_years=ComputationYears.STATUTORY" in statutory
    assert "the statutory oracle uses that count too" in statutory
    assert "no record can have this attribution" in statutory
    assert "`ss.benefits.aime(career, birth_year, params)`" in legacy
    assert "the legacy oracle always uses 35" in legacy
    assert "(35, the legacy oracle's)" in legacy
    # Person 2 (born 1920): the statutory oracle's AIME is not Track A's.
    assert "differs from Track A's" in statutory
    assert "for 1 of the 2 selected people: 1 of the 1 with fewer" in (
        " ".join(statutory.split())
    )
    assert "for 0 of the 2 selected people" in " ".join(legacy.split())
    assert "`statutory_415_b_2` and `legacy_fixed_35`" in statutory
    assert "`legacy_fixed_35` (its PIA" in legacy


def test_render_refuses_a_result_of_another_schema(fake_binding):
    result = _invented_result(fake_binding)
    result.pop("oracle")
    result["schema_version"] = "populace_dynamics.track_c.aime_agreement.v1"
    with pytest.raises(ValueError, match="aime_agreement.v1"):
        tc.render_results(result)
    # A 71c94743 (v2) result has an oracle record but the earlier artifact
    # binding; its prose belongs to the script at that commit.
    v2 = _invented_result(fake_binding)
    v2["schema_version"] = "populace_dynamics.track_c.aime_agreement.v2"
    with pytest.raises(ValueError, match="aime_agreement.v2"):
        tc.render_results(v2)
    no_oracle = _invented_result(fake_binding)
    no_oracle.pop("oracle")
    with pytest.raises(ValueError, match="render it with the script"):
        tc.render_results(no_oracle)


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
    for oracle in (STATUTORY, LEGACY):
        record, result = tc.compare_person(
            modern, _context(binding=binding, oracle=oracle)
        )
        assert record["status"] == "executed"
        assert result.engine_version == "0.2.2"
        assert record["exact_match"] is True
        assert record["attribution"] == tc.ATTR_EXACT
    early = _person(2, 1920)
    legacy, _ = tc.compare_person(
        early, _context(binding=binding, oracle=LEGACY)
    )
    assert legacy["candidate_computation_years"] == 26
    assert legacy["attribution"] == tc.ATTR_COUNT
    assert Decimal(legacy["axiom_aime"]) > legacy["track_a_oracle_aime"]
    statutory, _ = tc.compare_person(
        early, _context(binding=binding, oracle=STATUTORY)
    )
    assert statutory["oracle_computation_years"] == 26
    assert statutory["attribution"] == tc.ATTR_EXACT
    assert Decimal(statutory["axiom_aime"]) == statutory["oracle_aime"]
    assert statutory["request_sha256"] == legacy["request_sha256"]
