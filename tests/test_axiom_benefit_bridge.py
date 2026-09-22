"""Axiom benefit bridge: invented inputs with a fake engine, plus real Case A.

Every earnings amount, wage index and cohort member in the unit tests is
INVENTED for mechanics only.  The integration tests run the actual
axiom-rules-engine binary on SSA's published 2026 Case A and Case B inputs
and skip when that engine or its retained evidence is absent.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import populace_dynamics.axiom_benefit_bridge as bridge
from populace_dynamics.closed_cohort_history import ClosedCohortEarningsHistory
from populace_dynamics.engine.earnings_domain import EarningsDomainAdapter
from populace_dynamics.engine.steps import AgeSexMortalityModel
from populace_dynamics.forward_earnings_history import ForwardEarningsHistory
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap
from tests.test_closed_cohort_history import step
from tests.test_m6_engine_forward_earnings import _generator

# INVENTED series: plain increasing values, not SSA's published index.
INVENTED_AWI = bridge.AnnualSeries.from_mapping(
    "INVENTED wage index for tests",
    {year: f"{10000 + 500 * (year - 1951)}.25" for year in range(1951, 2025)},
)
INVENTED_BASE = bridge.AnnualSeries.from_mapping(
    "INVENTED contribution base for tests",
    {year: "100000" for year in range(1951, 2027)},
)
INVENTED_DECLARATION = bridge.ProjectedAmountDeclaration(
    "XTS",
    True,
    True,
    "INVENTED test amounts treated as USD creditable earnings",
    bridge.BINARY64_SHORTEST_ROUND_TRIP,
)


def _history(start, stop, *, amount="1000", synthetic=True):
    return bridge.CallerSuppliedHistory.from_mapping(
        "INVENTED test history",
        {year: amount for year in range(start, stop)},
        synthetic=synthetic,
    )


def _case_a_like():
    """INVENTED 1964 cohort shaped like SSA Case A (1986-2025 rows)."""
    determinations = bridge.OrdinaryRetirementDeterminations.from_birth_year(
        1964, 2026
    )
    return _history(1986, 2026).rows(), determinations


def _fake_response(request, values, *, engine_version="fake-engine-0"):
    outputs, selected = {}, []
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
        "engine_version": engine_version,
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


class RecordingRunner:
    """Fake engine: records each call and answers from the request."""

    def __init__(self, values=None, *, mutate=None, code=0, stderr=b""):
        self.calls = []
        self.values = values or {
            bridge.AIME_OUTPUT: "1234",
            bridge.PIA_OUTPUT: "567.8",
        }
        self.mutate = mutate
        self.code = code
        self.stderr = stderr

    def __call__(self, argv, wire, timeout):
        self.calls.append((tuple(argv), wire, timeout))
        request = json.loads(wire)
        response = _fake_response(request, self.values)
        if self.mutate is not None:
            response = self.mutate(response)
        body = (
            response
            if isinstance(response, bytes)
            else (json.dumps(response).encode())
        )
        return self.code, b"" if self.code else body, self.stderr


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
        files[role] = bridge.BoundFile(role, path, _sha(path))
    return bridge.AxiomEngineBinding(
        engine=files["engine"],
        artifacts=(
            files[bridge.ARTIFACT_AIME_PIA],
            files[bridge.ARTIFACT_AIME_ONLY],
        ),
        supporting=(files["module:invented.yaml"],),
        engine_source_commit="INVENTED-commit",
    )


def test_request_reproduces_the_case_a_wire_format():
    rows, determinations = _case_a_like()
    prepared = bridge.prepare_request(
        "invented-a", rows, determinations, INVENTED_AWI
    )
    request = prepared.request
    assert prepared.artifact_role == bridge.ARTIFACT_AIME_PIA
    assert prepared.outputs == (bridge.AIME_OUTPUT, bridge.PIA_OUTPUT)
    assert request["schema"] == "axiom-rules-engine/lifetime-request/v2"
    assert request["outputs"] == [bridge.AIME_OUTPUT, bridge.PIA_OUTPUT]
    assert request["calculation_period"] == {
        "period_kind": "custom",
        "name": "calendar_year",
        "start": "2026-01-01",
        "end": "2026-12-31",
    }
    assert request["output_period"] == request["calculation_period"]
    assert [p["start"][:4] for p in request["periods"]] == [
        str(year) for year in range(1986, 2026)
    ]
    assert (
        prepared.wire
        == (
            json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
    )
    per_year = (
        bridge.AIME_INPUT_PREFIX
        + "national_average_wage_index_for_computation_base_year"
    )
    for year, batch in zip(range(1986, 2026), request["batches"], strict=True):
        inputs = batch["inputs"]
        assert batch["row_count"] == 1
        assert batch["entity_ids"] == ["invented-a"]
        assert inputs[bridge.PIA_COHORT_INPUT] == {
            "kind": "bool",
            "values": [True],
        }
        prefix = bridge.AIME_INPUT_PREFIX
        assert inputs[prefix + "computation_base_year"] == {
            "kind": "integer",
            "values": [year],
        }
        assert inputs[
            prefix + "creditable_earnings_for_computation_base_year"
        ]["values"] == ["1000"]
        assert inputs[prefix + "indexing_year_for_aime"]["values"] == [2024]
        assert inputs[prefix + "year_individual_attained_age_21"][
            "values"
        ] == [1985]
        assert inputs[prefix + "year_individual_attained_age_62"][
            "values"
        ] == [2026]
        assert inputs[prefix + "year_of_death_or_later_sentinel"][
            "values"
        ] == [2026]
        assert inputs[
            prefix + "national_average_wage_index_for_indexing_year"
        ]["values"] == [INVENTED_AWI.get(2024)]
        # Case A omits the per-year index only after the indexing year.
        assert (per_year in inputs) is (year <= 2024)
        for name, value in bridge.SCOPED_ASSUMPTIONS.items():
            assert inputs[prefix + name] == {"kind": "bool", "values": [value]}
        assert len(inputs) == (16 if year <= 2024 else 15)
    kinds = [gap["kind"] for gap in prepared.recorded_gaps]
    assert kinds == [
        "creditable_ceiling_not_checked",
        "computation_base_years_before_elapsed_window_not_supplied",
    ]
    assert prepared.recorded_gaps[1]["years"] == "1964-1985"


def test_pia_is_requested_only_for_the_candidate_2026_cohort():
    determinations = bridge.OrdinaryRetirementDeterminations.from_birth_year(
        1959, 2026
    )
    prepared = bridge.prepare_request(
        "invented-b",
        _history(1981, 2026).rows(),
        determinations,
        INVENTED_AWI,
    )
    assert prepared.outputs == (bridge.AIME_OUTPUT,)
    assert prepared.artifact_role == bridge.ARTIFACT_AIME_ONLY
    assert all(
        bridge.PIA_COHORT_INPUT not in batch["inputs"]
        for batch in prepared.request["batches"]
    )


def test_ordinary_determinations_follow_the_case_a_b_conventions():
    determinations = bridge.OrdinaryRetirementDeterminations.from_birth_year(
        1959, 2026
    )
    assert (
        determinations.year_attained_age_21,
        determinations.year_attained_age_62,
        determinations.indexing_year,
        determinations.death_or_later_sentinel_year,
    ) == (1980, 2021, 2019, 2026)
    assert any("January 1" in text for text in determinations.derivations)
    with pytest.raises(bridge.BenefitBridgeRefusal, match="precedes"):
        bridge.OrdinaryRetirementDeterminations.from_birth_year(1964, 2025)
    with pytest.raises(TypeError):
        bridge.OrdinaryRetirementDeterminations.from_birth_year(1964.0, 2026)


def test_too_few_years_refuse_and_list_the_gap():
    _, determinations = _case_a_like()
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        bridge.prepare_request(
            "invented-short",
            _history(2000, 2026).rows(),
            determinations,
            INVENTED_AWI,
        )
    assert caught.value.gaps["missing_required_years"] == tuple(
        range(1986, 2000)
    )
    assert "1986-1999" in str(caught.value)


def test_interior_and_trailing_gaps_are_never_padded():
    rows, determinations = _case_a_like()
    holed = [row for row in rows if row.year not in (2000, 2025)]
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        bridge.prepare_request(
            "invented-holes", holed, determinations, INVENTED_AWI
        )
    assert caught.value.gaps["missing_required_years"] == (2000, 2025)


def test_rows_at_or_after_entitlement_are_not_computation_base_years():
    rows, determinations = _case_a_like()
    extra = rows + _history(2026, 2027).rows()
    with pytest.raises(bridge.BenefitBridgeRefusal, match="2026"):
        bridge.prepare_request(
            "invented-late", extra, determinations, INVENTED_AWI
        )
    with pytest.raises(ValueError, match="once"):
        bridge.prepare_request(
            "invented-dup", rows + rows[:1], determinations, INVENTED_AWI
        )


def test_missing_wage_index_years_refuse():
    rows, determinations = _case_a_like()
    thinned = bridge.AnnualSeries(
        "INVENTED thinned index",
        tuple(item for item in INVENTED_AWI.values if item[0] != 1990),
    )
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        bridge.prepare_request("invented-awi", rows, determinations, thinned)
    assert caught.value.gaps["missing_wage_index_years"] == (1990,)


def test_leading_gap_needs_an_exact_explicit_acknowledgement():
    determinations = bridge.OrdinaryRetirementDeterminations.from_birth_year(
        1959, 2026
    )
    rows = _history(1986, 2026).rows()
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        bridge.prepare_request("invented", rows, determinations, INVENTED_AWI)
    assert caught.value.gaps["missing_required_years"] == tuple(
        range(1981, 1986)
    )
    wrong = bridge.LeadingGapAcknowledgement((1982, 1983), "INVENTED")
    with pytest.raises(bridge.BenefitBridgeRefusal, match="do not equal"):
        bridge.prepare_request(
            "invented", rows, determinations, INVENTED_AWI, leading_gap=wrong
        )
    exact = bridge.LeadingGapAcknowledgement(
        tuple(range(1981, 1986)), "INVENTED source lists no earlier rows"
    )
    prepared = bridge.prepare_request(
        "invented", rows, determinations, INVENTED_AWI, leading_gap=exact
    )
    recorded = {gap["kind"]: gap for gap in prepared.recorded_gaps}
    acknowledged = recorded["acknowledged_unsupplied_elapsed_window_years"]
    assert acknowledged["years"] == "1981-1985"
    assert acknowledged["statement"] == exact.statement
    assert recorded[
        "computation_base_years_before_elapsed_window_not_supplied"
    ]["years"] == ("1959-1980")
    with pytest.raises(ValueError, match="contiguous"):
        bridge.LeadingGapAcknowledgement((1981, 1983), "INVENTED")


def test_contribution_base_is_a_check_never_a_cap():
    rows, determinations = _case_a_like()
    prepared = bridge.prepare_request(
        "invented",
        rows,
        determinations,
        INVENTED_AWI,
        contribution_base=INVENTED_BASE,
    )
    assert "creditable_ceiling_not_checked" not in {
        gap["kind"] for gap in prepared.recorded_gaps
    }
    high = [
        (
            bridge.EarningsRow(r.year, Decimal("100000.01"), r.source, True)
            if r.year == 1990
            else r
        )
        for r in rows
    ]
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        bridge.prepare_request(
            "invented",
            high,
            determinations,
            INVENTED_AWI,
            contribution_base=INVENTED_BASE,
        )
    assert caught.value.gaps["above_creditable_ceiling_years"] == (1990,)
    partial = bridge.AnnualSeries(
        "INVENTED partial base",
        tuple(item for item in INVENTED_BASE.values if item[0] >= 2000),
    )
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        bridge.prepare_request(
            "invented",
            rows,
            determinations,
            INVENTED_AWI,
            contribution_base=partial,
        )
    assert caught.value.gaps["unchecked_creditable_ceiling_years"] == tuple(
        range(1986, 2000)
    )


def test_amounts_are_exact_and_binary64_encoding_is_explicit():
    with pytest.raises(TypeError):
        bridge.EarningsRow(2000, 0.1, "INVENTED", True)
    with pytest.raises(ValueError):
        bridge.EarningsRow(2000, Decimal("-1"), "INVENTED", True)
    bits = (0.1).hex()
    exact = bridge.binary64_decimal(bits, bridge.BINARY64_EXACT)
    shortest = bridge.binary64_decimal(
        bits, bridge.BINARY64_SHORTEST_ROUND_TRIP
    )
    assert exact == Decimal(0.1) and shortest == Decimal("0.1")
    assert bridge.binary64_decimal(
        (21550.0).hex(), bridge.BINARY64_SHORTEST_ROUND_TRIP
    ) == Decimal("21550")
    row = bridge.EarningsRow(
        2000,
        shortest,
        "INVENTED",
        True,
        bits,
        bridge.BINARY64_SHORTEST_ROUND_TRIP,
    )
    assert row.document()["amount"] == "0.1"
    with pytest.raises(ValueError, match="encoded"):
        bridge.EarningsRow(
            2000,
            exact,
            "INVENTED",
            True,
            bits,
            bridge.BINARY64_SHORTEST_ROUND_TRIP,
        )
    with pytest.raises(ValueError, match="encoding"):
        bridge.EarningsRow(
            2000, shortest, "INVENTED", True, None, bridge.BINARY64_EXACT
        )
    with pytest.raises(ValueError, match="unsupported"):
        bridge.binary64_decimal(bits, "rounded_to_cents")


def test_execute_parses_outputs_and_records_provenance(fake_binding):
    rows, determinations = _case_a_like()
    prepared = bridge.prepare_request(
        "invented-a", rows, determinations, INVENTED_AWI
    )
    runner = RecordingRunner()
    result = bridge.execute_request(prepared, fake_binding, runner=runner)
    ((argv, wire, timeout),) = runner.calls
    assert argv == (
        str(fake_binding.engine.path),
        "run-lifetime",
        "--artifact",
        str(fake_binding.artifact(bridge.ARTIFACT_AIME_PIA).path),
    )
    assert wire == prepared.wire and timeout == 60.0
    assert result.aime == Decimal("1234")
    assert result.ordinary_pia_before_cola == Decimal("567.8")
    document = result.document()
    provenance = document["provenance"]
    assert document["aime"] == "1234"
    assert document["ordinary_pia_before_cola"] == "567.8"
    assert provenance["engine_sha256"] == fake_binding.engine.sha256
    assert provenance["artifact_sha256"] == (
        fake_binding.artifact(bridge.ARTIFACT_AIME_PIA).sha256
    )
    assert provenance["module_sha256"] == {
        "module:invented.yaml": fake_binding.supporting[0].sha256
    }
    assert provenance["candidates_accepted"] is False
    assert "unaccepted" in provenance["candidate_status"]
    assert provenance["request_sha256"] == prepared.request_sha256
    assert provenance["policy_arithmetic_in_bridge"] is False
    assert document["synthetic_rows"] == 40


def test_aime_only_people_use_the_aime_only_artifact(fake_binding):
    determinations = bridge.OrdinaryRetirementDeterminations.from_birth_year(
        1959, 2026
    )
    prepared = bridge.prepare_request(
        "invented-b", _history(1981, 2026).rows(), determinations, INVENTED_AWI
    )
    runner = RecordingRunner()
    result = bridge.execute_request(prepared, fake_binding, runner=runner)
    assert runner.calls[0][0][-1] == str(
        fake_binding.artifact(bridge.ARTIFACT_AIME_ONLY).path
    )
    assert result.ordinary_pia_before_cola is None
    assert result.pia_status.startswith("not_requested")


def _without_output(response):
    response["outputs"].pop(bridge.PIA_OUTPUT)
    return response


def _set(path, value):
    def mutate(response):
        target = response
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        return response

    return mutate


@pytest.mark.parametrize(
    "mutate",
    [
        _set(("schema",), "axiom-rules-engine/lifetime-response/v1"),
        _set(("entity_ids",), ["someone-else"]),
        _set(("row_count",), True),
        _set(("periods",), []),
        _set(("artifact_format_version",), 3),
        _set(("engine_version",), ""),
        _set(("extra",), 1),
        _without_output,
        _set(("outputs", bridge.AIME_OUTPUT, "column", "values"), [1234]),
        _set(("outputs", bridge.AIME_OUTPUT, "column", "values"), ["1e3"]),
        _set(("outputs", bridge.AIME_OUTPUT, "unit"), "XTS"),
        _set(("selected_versions", 0, "effective_from"), "2030-01-01"),
        _set(("selected_versions",), []),
        lambda response: json.dumps(response)
        .replace('"schema"', '"schema": "x", "schema"', 1)
        .encode(),
    ],
)
def test_malformed_responses_are_rejected(fake_binding, mutate):
    rows, determinations = _case_a_like()
    prepared = bridge.prepare_request(
        "invented-a", rows, determinations, INVENTED_AWI
    )
    with pytest.raises(bridge.AxiomExecutionError):
        bridge.execute_request(
            prepared, fake_binding, runner=RecordingRunner(mutate=mutate)
        )


def test_engine_failures_carry_the_engine_message(fake_binding):
    rows, determinations = _case_a_like()
    prepared = bridge.prepare_request(
        "invented-a", rows, determinations, INVENTED_AWI
    )
    stderr = json.dumps(
        {
            "category": "invalid_request",
            "field": None,
            "message": "INVENTED engine complaint",
            "schema": "axiom-rules-engine/lifetime-error/v1",
        }
    ).encode()
    with pytest.raises(bridge.AxiomExecutionError, match="INVENTED engine"):
        bridge.execute_request(
            prepared,
            fake_binding,
            runner=RecordingRunner(code=1, stderr=stderr),
        )


def test_changed_bound_files_block_or_invalidate_execution(fake_binding):
    rows, determinations = _case_a_like()
    prepared = bridge.prepare_request(
        "invented-a", rows, determinations, INVENTED_AWI
    )
    module = fake_binding.supporting[0].path
    original = module.read_text()
    module.write_text("changed\n")
    runner = RecordingRunner()
    with pytest.raises(bridge.BindingMismatch, match="module:invented"):
        bridge.execute_request(prepared, fake_binding, runner=runner)
    assert runner.calls == []
    module.write_text(original)

    def tampering(argv, wire, timeout):
        Path(argv[-1]).write_text('{"changed": true}')
        return RecordingRunner()(argv, wire, timeout)

    with pytest.raises(bridge.BindingMismatch, match="aime_pia"):
        bridge.execute_request(prepared, fake_binding, runner=tampering)


def test_subprocess_path_runs_an_executable_fake_engine(tmp_path):
    """The default runner really spawns the bound binary with stdin wire."""
    script = tmp_path / "fake-axiom-rules-engine"
    received = tmp_path / "received.json"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "sys.path.insert(0, " + repr(str(Path(__file__).parent.parent)) + ")\n"
        "from tests.test_axiom_benefit_bridge import _fake_response\n"
        "wire = sys.stdin.buffer.read()\n"
        f"open({str(received)!r}, 'wb').write(wire)\n"
        "assert sys.argv[1:3] == ['run-lifetime', '--artifact']\n"
        "values = {'us:statutes/42/415/b#average_indexed_monthly_earnings':"
        " '42', 'us:statutes/42/415/a#ordinary_pia_before_cola': '37.8'}\n"
        "print(json.dumps(_fake_response(json.loads(wire), values)))\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    files = {}
    for role in (bridge.ARTIFACT_AIME_PIA, bridge.ARTIFACT_AIME_ONLY):
        path = tmp_path / role
        path.write_text("{}")
        files[role] = bridge.BoundFile(role, path, _sha(path))
    binding = bridge.AxiomEngineBinding(
        engine=bridge.BoundFile("engine", script, _sha(script)),
        artifacts=tuple(files.values()),
        supporting=(),
        engine_source_commit="INVENTED-commit",
    )
    rows, determinations = _case_a_like()
    prepared = bridge.prepare_request(
        "invented-a", rows, determinations, INVENTED_AWI
    )
    result = bridge.execute_request(prepared, binding)
    assert received.read_bytes() == prepared.wire
    assert (result.aime, result.ordinary_pia_before_cola) == (
        Decimal("42"),
        Decimal("37.8"),
    )


def test_reviewed_binding_pins_cannot_be_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv(bridge.ENGINE_ROOT_ENV, str(tmp_path / "engine"))
    monkeypatch.setenv(bridge.EVIDENCE_DIR_ENV, str(tmp_path / "evidence"))
    binding = bridge.reviewed_case_a_binding()
    assert binding.engine.path == (
        tmp_path / "engine/target/release/axiom-rules-engine"
    )
    assert binding.engine.sha256 == bridge.REVIEWED_PINS["engine"]
    assert binding.engine_source_commit == (
        bridge.REVIEWED_ENGINE_SOURCE_COMMIT
    )
    assert binding.candidates_accepted is False
    assert len(binding.missing_files()) == len(binding.files)
    with pytest.raises(bridge.BindingMismatch, match="absent"):
        binding.verify()


# ---------------------------------------------------------------------------
# Retained cohort histories (INVENTED people produced by actual engine steps)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def invented_cohort():
    """Four INVENTED people; key 10 is removed by mortality in 2015."""
    mapping = PersonIdentityMap.from_identities(
        [
            PersonIdentity("int64", -(2**63)),
            PersonIdentity("string", "001"),
            *(PersonIdentity("uint64", 2**64 - 1 - i) for i in range(19)),
        ]
    )
    generator = EarningsDomainAdapter(_generator())
    initial = pd.DataFrame(
        {
            "person_id": np.array([20, 10, 1, 0], dtype="int64"),
            "year": np.full(4, 2014, dtype="int64"),
            "age": np.array([62, 36, 61, 30], dtype="int64"),
            "sex": ["female", "male", "female", "female"],
        }
    )
    frame = generator.materialize_initial_frame(initial)
    baseline = ForwardEarningsHistory.start(
        mapping,
        frame,
        realization_id="invented-cohort",
        generator_digest="a" * 64,
        source_contract_digest="b" * 64,
        lineage_digest="c" * 64,
        unit="XTS",
        price_basis="nominal",
    )
    model = AgeSexMortalityModel(
        ((0, 34), (35, 120)),
        {
            ("0-34", "female"): 0.0,
            ("0-34", "male"): 0.0,
            ("35+", "female"): 0.0,
            ("35+", "male"): 1.0,
        },
    )
    cohort = ClosedCohortEarningsHistory.start(baseline, draw_index=3)
    for year in range(2015, 2023):
        frame, mortality, _, _ = step(frame, year, generator, baseline, model)
        cohort = cohort.append(
            mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
        )
    return cohort


def _zero_supplements(demographics):
    return {
        key: bridge.CallerSuppliedHistory.from_mapping(
            "SYNTHETIC explicit zeros",
            {year: 0 for year in range(demo.birth_year + 22, 2014)},
            synthetic=True,
        )
        for key, demo in demographics.items()
        if demo.birth_year + 22 < 2014
    }


def test_demographics_come_from_the_retained_2014_ages(invented_cohort):
    demographics = bridge.cohort_demographics(invented_cohort)
    assert {key: (d.birth_year, d.sex) for key, d in demographics.items()} == {
        0: (1984, "female"),
        1: (1953, "female"),
        10: (1978, "male"),
        20: (1952, "female"),
    }
    empty = ClosedCohortEarningsHistory.start(
        invented_cohort.baseline, draw_index=3
    )
    with pytest.raises(bridge.BenefitBridgeRefusal, match="no ages"):
        bridge.cohort_demographics(empty)


def _prepare(cohort, key, **overrides):
    demographics = bridge.cohort_demographics(cohort)
    options = {
        "demographics": demographics,
        "entitlement_age": 70,
        "declaration": INVENTED_DECLARATION,
        "wage_index": INVENTED_AWI,
        "contribution_base": INVENTED_BASE,
        "pre_projection": _zero_supplements(demographics).get(key),
    }
    options.update(overrides)
    return bridge.prepare_cohort_person(cohort, key, **options)


def test_projected_labor_income_needs_an_explicit_declaration(
    invented_cohort,
):
    with pytest.raises(bridge.BenefitBridgeRefusal, match="Declaration"):
        _prepare(invented_cohort, 20, declaration=None)
    usd = bridge.ProjectedAmountDeclaration("USD", True, True, "INVENTED")
    with pytest.raises(bridge.BenefitBridgeRefusal, match="unit is XTS"):
        _prepare(invented_cohort, 20, declaration=usd)
    refused = bridge.ProjectedAmountDeclaration("XTS", False, True, "INVENTED")
    with pytest.raises(bridge.BenefitBridgeRefusal, match="does not permit"):
        _prepare(invented_cohort, 20, declaration=refused)


def test_missing_birth_year_refuses(invented_cohort):
    demographics = bridge.cohort_demographics(invented_cohort)
    demographics.pop(20)
    with pytest.raises(bridge.BenefitBridgeRefusal, match="birth year"):
        _prepare(invented_cohort, 20, demographics=demographics)


def test_pre_projection_gap_is_recorded_not_filled(invented_cohort):
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        _prepare(invented_cohort, 20, pre_projection=None)
    assert caught.value.gaps == {
        "missing_pre_projection_years": tuple(range(1974, 2014))
    }
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        _prepare(invented_cohort, 1, entitlement_age=75)
    assert caught.value.gaps["missing_post_projection_years"] == tuple(
        range(2023, 2028)
    )
    with pytest.raises(ValueError, match="precede 2014"):
        _prepare(invented_cohort, 20, pre_projection=_history(2010, 2015))


def test_explicit_supplement_carries_projected_bits(invented_cohort):
    prepared = _prepare(invented_cohort, 20)
    person = next(
        h for h in invented_cohort.histories if h.roster_keys == (20,)
    )
    assert prepared.person_id == "dynamics-person-20"
    assert prepared.calculation_year == 2022
    assert prepared.outputs == (bridge.AIME_OUTPUT,)
    projected = [r for r in prepared.rows if r.amount_hex is not None]
    synthetic = [r for r in prepared.rows if r.amount_hex is None]
    assert [r.year for r in synthetic] == list(range(1974, 2014))
    assert all(r.synthetic and r.amount == 0 for r in synthetic)
    assert [r.year for r in projected] == list(range(2014, 2022))
    for row, observation in zip(projected, person.observations, strict=False):
        assert row.amount_hex == observation.amount_hex
        assert row.amount == Decimal(float.fromhex(observation.amount_hex))
        assert row.encoding == bridge.BINARY64_SHORTEST_ROUND_TRIP
        assert row.source == "projected:invented-cohort"
    assert any(
        "2022 are not computation base years" in n for n in prepared.notes
    )
    assert any("uint64" in n or "int64" in n for n in prepared.notes)


def test_mortality_removal_and_unavailable_amounts_refuse(invented_cohort):
    with pytest.raises(bridge.BenefitBridgeRefusal, match="mortality step"):
        _prepare(invented_cohort, 10)
    with pytest.raises(bridge.BenefitBridgeRefusal) as caught:
        _prepare(invented_cohort, 0)
    assert caught.value.gaps["unavailable_projected_years"] == tuple(
        range(2014, 2023)
    )
    with pytest.raises(bridge.BenefitBridgeRefusal, match="no projected"):
        _prepare(invented_cohort, 20, entitlement_age=62)


def test_run_cohort_records_every_person(invented_cohort, fake_binding):
    demographics = bridge.cohort_demographics(invented_cohort)
    runner = RecordingRunner()
    outcomes = bridge.run_cohort(
        invented_cohort,
        entitlement_age=70,
        declaration=INVENTED_DECLARATION,
        wage_index=INVENTED_AWI,
        binding=fake_binding,
        contribution_base=INVENTED_BASE,
        pre_projection=_zero_supplements(demographics),
        runner=runner,
    )
    status = {o.dynamics_person_key: o.status for o in outcomes}
    assert status == {
        0: "refused",
        1: "executed",
        10: "refused",
        20: "executed",
    }
    assert len(runner.calls) == 2
    executed = next(o for o in outcomes if o.dynamics_person_key == 1)
    document = executed.document()
    assert document["source_identity"] == "string:001"
    assert document["result"]["aime"] == "1234"
    assert document["result"]["ordinary_pia_before_cola"] is None
    refused = next(o for o in outcomes if o.dynamics_person_key == 0)
    assert refused.document()["gaps"]["unavailable_projected_years"] == (
        "2014-2022"
    )
    Path(fake_binding.engine.path).write_text("changed")
    with pytest.raises(bridge.BindingMismatch):
        bridge.run_cohort(
            invented_cohort,
            entitlement_age=70,
            declaration=INVENTED_DECLARATION,
            wage_index=INVENTED_AWI,
            binding=fake_binding,
            pre_projection=_zero_supplements(demographics),
            runner=runner,
        )


# ---------------------------------------------------------------------------
# Actual Axiom engine: SSA's published 2026 Case A and Case B
# ---------------------------------------------------------------------------

CASE_A_TRANSPORT_SHA256 = (
    "7471fb22622078762b5d2064c6b09df7220ebb580a2bbadac8382f9de87b873e"
)
CASE_B_TRANSPORT_SHA256 = (
    "daf051a82bff8f27f0e107fa4ec58bb8c3f7dd7540356216422d9766e818042c"
)
RETAINED_CASE_A_REQUEST_SHA256 = (
    "f5bf1279d6e47d23dd247af0e03007e22d562d78d64463887dfc315902e47ea4"
)
RETAINED_CASE_A_STDOUT_SHA256 = (
    "fafc8d3151ff6a0d2707dfe44c25b912fcd1765a7c90122a547aa96614a57e92"
)
RETAINED_CASE_B_REQUEST_SHA256 = (
    "d738bb71b77b753d4408fafa65fb716d1dc67f321e73011954ed2488dff15811"
)
RETAINED_CASE_B_STDOUT_SHA256 = (
    "ad87a6c2269624c3c57bfc58d4251dfd2578a796bdc88d3295e9907555389bfb"
)


def _published_case(name, digest):
    evidence = Path(
        os.environ.get(bridge.EVIDENCE_DIR_ENV) or bridge.DEFAULT_EVIDENCE_DIR
    ).expanduser()
    binding = bridge.reviewed_case_a_binding()
    transport = evidence / "ssa-aime-pia-first-comparison-20260922" / name
    missing = [str(p) for p in binding.missing_files()]
    if not transport.is_file():
        missing.append(str(transport))
    if missing:
        pytest.skip(
            "actual Axiom engine or evidence absent: " + ", ".join(missing)
        )
    assert _sha(transport) == digest
    source = json.loads(transport.read_text())
    rows = source["annual_observations"]
    history = bridge.CallerSuppliedHistory.from_mapping(
        source["benchmark"],
        {row["year"]: row["nominal_covered_earnings_dollars"] for row in rows},
        synthetic=False,
    )
    wage_index = bridge.AnnualSeries.from_mapping(
        "SSA AWI transported with " + source["benchmark"],
        {
            row["year"]: row["awi_decimal"]
            for row in rows
            if row["awi_decimal"]
        },
        source_sha256=digest,
    )
    return binding, source, history, wage_index


def test_actual_engine_reproduces_published_case_a_through_the_bridge():
    binding, source, history, wage_index = _published_case(
        "primary-source-2026-case-a/source-data-transport.json",
        CASE_A_TRANSPORT_SHA256,
    )
    determinations = bridge.OrdinaryRetirementDeterminations.from_birth_year(
        int(source["cohort_facts"]["birth_year"]),
        int(source["cohort_facts"]["calculation_year"]),
    )
    prepared = bridge.prepare_request(
        "ssa_2026_case_a", history.rows(), determinations, wage_index
    )
    # Byte-identical to the retained request that first matched Case A.
    assert prepared.request_sha256 == RETAINED_CASE_A_REQUEST_SHA256
    result = bridge.execute_request(prepared, binding)
    assert result.aime == Decimal("5825")
    assert result.ordinary_pia_before_cola == Decimal("2609.80")
    assert result.stdout_sha256 == RETAINED_CASE_A_STDOUT_SHA256
    assert hashlib.sha256(result.stdout).hexdigest() == result.stdout_sha256
    assert result.stderr == ""
    provenance = result.document()["provenance"]
    assert provenance["engine_sha256"] == bridge.REVIEWED_PINS["engine"]
    assert provenance["artifact_sha256"] == (
        bridge.REVIEWED_PINS[bridge.ARTIFACT_AIME_PIA]
    )
    assert provenance["candidates_accepted"] is False
    assert provenance["engine_version"] == "0.2.2"


def test_actual_engine_reproduces_published_case_b_aime_only_path():
    binding, source, history, wage_index = _published_case(
        "primary-source-2026-case-b/source-data-transport-v2.json",
        CASE_B_TRANSPORT_SHA256,
    )
    determinations = bridge.OrdinaryRetirementDeterminations.from_birth_year(
        int(source["cohort_facts"]["birth_year"]),
        int(source["cohort_facts"]["calculation_year"]),
    )
    with pytest.raises(bridge.BenefitBridgeRefusal, match="1981-1985"):
        bridge.prepare_request(
            "ssa_2026_case_b", history.rows(), determinations, wage_index
        )
    prepared = bridge.prepare_request(
        "ssa_2026_case_b",
        history.rows(),
        determinations,
        wage_index,
        leading_gap=bridge.LeadingGapAcknowledgement(
            tuple(range(1981, 1986)),
            "SSA's published Case B table lists no earnings before 1986",
        ),
    )
    assert prepared.request_sha256 == RETAINED_CASE_B_REQUEST_SHA256
    result = bridge.execute_request(prepared, binding)
    assert result.aime == Decimal("11463")
    assert result.ordinary_pia_before_cola is None
    assert result.stdout_sha256 == RETAINED_CASE_B_STDOUT_SHA256
