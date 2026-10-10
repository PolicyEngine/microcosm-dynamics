"""Track M end to end on an INVENTED cohort with INVENTED parameters.

The cohort and every parameter are **INVENTED** (``invented.
invented_track_m_inputs`` and ``invented.invented_parameters``): no PSID,
Census, SSA or comparator value.  These tests run every registered row
through the pipeline and check its guards; the dry-run script
(``scripts/track_m_dry_run.py``) runs the same cohort with the real
parameters.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from populace_dynamics.min_benefit_track_m import (
    COVERED_EARNINGS_DISCLOSURE,
    evaluation,
    invented,
    pipeline,
    rules,
    specification,
    tabulation,
)
from populace_dynamics.min_benefit_track_m import policy as pol

PARAMETERS, COLA = invented.invented_parameters()
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
#: The blockers ``m1-ratified-1``'s block listed when it was ratified; the
#: registered-commit edit (2026-09-27) dropped both.
BLOCKERS_AT_RATIFICATION = (
    "registration_package_m10_needs_the_comparator_seal_hash",
    "issue_42_registration_absent",
)


def _committed() -> dict:
    return json.loads(json.dumps(specification.m1_parameter_block()))


def _blocked() -> dict:
    """The committed block as ratified, before the registered-commit
    edit: its ``blocked_by`` named the two blockers."""

    return {**_committed(), "blocked_by": list(BLOCKERS_AT_RATIFICATION)}


@pytest.fixture(scope="module")
def cohort():
    return invented.invented_track_m_inputs(
        seed=7, n_family_units=160, params=PARAMETERS.params, cola_rates=COLA
    )


@pytest.fixture(scope="module")
def result(cohort):
    return pipeline.run_track_m(cohort, PARAMETERS, data_provenance="invented")


def test_every_registered_row_runs(result):
    assert list(result["rows"]) == list(pol.REGISTERED_ROWS)
    assert result["header"] == "INVENTED DATA - NOT A COMPARISON"
    assert result["labels"][0] == tabulation.INVENTED_DATA_LABEL
    assert result["disclosure"] == COVERED_EARNINGS_DISCLOSURE
    for row, entry in result["rows"].items():
        assert entry["change_from_ms0"] == pol.REGISTERED_ROWS[row]
        assert len(entry["tabulation"]["cells"]) == 12
        assert entry["tabulation"]["row_id"] == row
    headline = next(
        cell
        for cell in result["rows"]["MS0"]["tabulation"]["cells"]
        if cell["headline"]
    )
    assert (headline["option"], headline["row"]) == (2, "all")
    assert result["headline"]["share_percent"] == headline["share_percent"]
    departed = {
        row: entry["rulings_departed_from"]
        for row, entry in result["rows"].items()
    }
    assert departed == {
        "MS0": [],
        "MS1": ["policy_year"],
        "MS2": ["order"],
        "MS3": ["counting_rule"],
        "MS4": [],
        "MS5": [],
        "MS6": [],
    }
    assert len(result["max_rulings"]) == len(pol.MAX_RULINGS)
    # MS5 reads the benefit-implied PIA of its in-scope records, and no
    # other row reads any
    sources = {
        row: entry["diagnostics"]["pia_source_by_record"]
        for row, entry in result["rows"].items()
    }
    assert sources["MS5"]["benefit_implied"] > 0
    assert all(
        counts["benefit_implied"] == 0
        for row, counts in sources.items()
        if row != "MS5"
    )
    json.dumps(result, allow_nan=False)


def test_deductions_hold_on_the_invented_cohort(result):
    """Deductions from the rules (unit tests, not results).

    Option 4's share is at least option 2's and option 5's at least
    option 3's in every cell: the worker flags nest (M1 section 8); a
    flagged worker's option PIA is the minimum, at least as high under
    the generous schedule, so a linked benefit paid under option 2 is
    paid under option 4 unless the person's own PIA moves onto option 4's
    minimum, and then they receive it through their own record if paid
    their own benefit, as every person of the invented cohort with an own
    record is.  MS3 counts a subset of MS0's receivers (receipt through
    the own PIA only).  MS4's window lies inside MS0's, which by the same
    argument makes MS4's receivers a subset of MS0's here.
    """

    def shares(row):
        return {
            (c["option"], c["row"]): c["share_percent"]
            for c in result["rows"][row]["tabulation"]["cells"]
        }

    ms0, ms3, ms4 = shares("MS0"), shares("MS3"), shares("MS4")
    for cell in ("all", "men", "women"):
        assert ms0[(4, cell)] >= ms0[(2, cell)]
        assert ms0[(5, cell)] >= ms0[(3, cell)]
        for option in (2, 3, 4, 5):
            assert ms3[(option, cell)] <= ms0[(option, cell)] + 1e-9
            assert ms4[(option, cell)] <= ms0[(option, cell)] + 1e-9
    for entry in result["rows"].values():
        assert entry["diagnostics"]["worker_flag_nesting_violations"] == 0


def test_a_missing_threshold_year_is_refused_before_any_computation(
    cohort, monkeypatch
):
    early = evaluation.WorkerRecord(
        "EARLY",
        1936,
        rules.BASIS_OLD_AGE,
        2004,
        {year: 30_000.0 for year in range(1968, 1997)},
    )
    with_early = dataclasses.replace(
        cohort, workers={**cohort.workers, "EARLY": early}
    )

    def never(*args, **kwargs):
        raise AssertionError("evaluated before the threshold check")

    monkeypatch.setattr(pipeline, "evaluate", never)
    with pytest.raises(rules.ThresholdYearMissingError, match="1998"):
        pipeline.run_track_m(
            with_early, PARAMETERS, data_provenance="invented"
        )


def test_the_registered_path_refuses_before_any_computation(
    cohort, monkeypatch
):
    def never(*args, **kwargs):
        raise AssertionError("evaluated before the provenance check")

    monkeypatch.setattr(pipeline, "evaluate", never)
    psid_kind = dataclasses.replace(
        cohort, provenance_kind=evaluation.PSID_FILES
    )
    for inputs, provenance, pointer, block, match in (
        (cohort, "registered_real", POINTER, None, "contradicts"),
        (psid_kind, "invented", None, None, "invented data"),
        (psid_kind, "registered_real", None, None, "registration pointer"),
        (
            psid_kind,
            "registered_real",
            POINTER.replace("/42#", "/420#"),
            None,
            "registration pointer",
        ),
        # a block that still lists blockers (the block as ratified)
        (psid_kind, "registered_real", POINTER, _blocked(), "still blocked"),
    ):
        with pytest.raises(tabulation.TrackMTabulationError, match=match):
            pipeline.run_track_m(
                inputs,
                PARAMETERS,
                data_provenance=provenance,
                registration_pointer=pointer,
                specification=block,
            )
    # Under the committed block, which lists no blocker since the
    # registered-commit edit, PSID-kind records with the issue #42 pointer
    # pass the provenance guard; the next refusal, still before anything
    # is evaluated, is the registered run's need for d430's sensitivity.
    with pytest.raises(ValueError, match="d430 sensitivity"):
        pipeline.run_track_m(
            psid_kind,
            PARAMETERS,
            data_provenance="registered_real",
            registration_pointer=POINTER,
        )
    with pytest.raises(ValueError, match="MS0"):
        pipeline.run_track_m(
            cohort, PARAMETERS, data_provenance="invented", rows=("MS1",)
        )
    with pytest.raises(ValueError, match="each once"):
        pipeline.run_track_m(
            cohort,
            PARAMETERS,
            data_provenance="invented",
            rows=("MS0", "MS0"),
        )


def test_a_registered_run_reports_every_row_with_the_registered_seeds(
    cohort, monkeypatch
):
    """Even under the ratified, unblocked specification (an in-memory copy
    of the committed block), the registered path refuses a subset of rows
    or other floor seeds before evaluating anything."""

    def never(*args, **kwargs):
        raise AssertionError("evaluated before the registered-run checks")

    monkeypatch.setattr(pipeline, "evaluate", never)
    block = json.loads(json.dumps(specification.m1_parameter_block()))
    block.update(
        status="ratified_frozen", version="m1-ratified-1", blocked_by=[]
    )
    assert block == specification.m1_parameter_block()
    psid_kind = dataclasses.replace(
        cohort, provenance_kind=evaluation.PSID_FILES
    )
    common = {
        "data_provenance": "registered_real",
        "registration_pointer": POINTER,
        "specification": block,
    }
    with pytest.raises(ValueError, match="every registered row"):
        pipeline.run_track_m(
            psid_kind, PARAMETERS, rows=("MS0", "MS1"), **common
        )
    with pytest.raises(ValueError, match="every registered row"):
        pipeline.run_track_m(
            psid_kind,
            PARAMETERS,
            rows=tuple(reversed(pol.REGISTERED_ROWS)),
            **common,
        )
    with pytest.raises(ValueError, match="floor seeds"):
        pipeline.run_track_m(
            psid_kind, PARAMETERS, floor_seeds=(0, 1, 2, 3, 4), **common
        )


def test_psid_hashed_records_are_evaluated_only_under_the_committed_block(
    cohort, monkeypatch
):
    """Records carrying PSID file hashes reach no evaluation outside the
    registered run, without the issue #42 pointer, or under a supplied
    block other than the committed one, even a block the gate would pass
    (here the committed block with another snapshot, a field the gate does
    not hold to the code).  A supplied copy equal to the committed block
    is the committed block: it passes this guard, and the next refusal is
    d430's sensitivity.  Nothing is evaluated (the records are INVENTED)."""

    def never(*args, **kwargs):
        raise AssertionError("evaluated before the guards")

    monkeypatch.setattr(pipeline, "evaluate", never)
    hashed = dataclasses.replace(
        cohort,
        provenance_kind=evaluation.PSID_FILES,
        source={
            **dict(cohort.source),
            pipeline.PSID_FILES_SOURCE_KEY: {"INVENTED.txt": "0" * 64},
        },
    )
    supplied = {
        **_committed(),
        "snapshot": {"wave": 2021, "income_year": 2020},
    }
    specification.check_specification_for_registered_run(supplied)
    registered = {
        "data_provenance": "registered_real",
        "registration_pointer": POINTER,
    }
    with pytest.raises(ValueError, match="only by the registered run"):
        pipeline.run_track_m(hashed, PARAMETERS, data_provenance="invented")
    with pytest.raises(ValueError, match="supplied block must equal it"):
        pipeline.run_track_m(
            hashed, PARAMETERS, specification=supplied, **registered
        )
    with pytest.raises(ValueError, match="supplied block must equal it"):
        pipeline.run_track_m(
            hashed, PARAMETERS, specification=_blocked(), **registered
        )
    with pytest.raises(
        tabulation.TrackMTabulationError, match="registration pointer"
    ):
        pipeline.run_track_m(
            hashed, PARAMETERS, data_provenance="registered_real"
        )
    for block in (None, _committed()):
        with pytest.raises(ValueError, match="d430 sensitivity"):
            pipeline.run_track_m(
                hashed, PARAMETERS, specification=block, **registered
            )


def test_the_invented_cohort_has_every_shape_the_rules_need(cohort):
    again = invented.invented_track_m_inputs(
        seed=7, n_family_units=160, params=PARAMETERS.params, cola_rates=COLA
    )
    assert again.persons == cohort.persons
    assert again.workers == cohort.workers
    bases = {record.basis for record in cohort.workers.values()}
    assert bases == set(rules.BASES)
    policies = [pol.policy_for_row(row) for row in pol.REGISTERED_ROWS]
    needed = evaluation.needed_threshold_years(
        cohort.workers.values(), policies
    )
    assert min(needed) >= 2003 and max(needed) <= 2022
    assert any(record.ms5_in_scope for record in cohort.workers.values())
    assert any(record.unresolved for record in cohort.workers.values())
    for record in cohort.workers.values():
        assert not {1997, 1999} & set(record.next_wave)
        assert all(year < 1997 or year % 2 == 0 for year in record.observed)
        assert min(record.observed, default=1968) >= 1968
    persons = cohort.persons
    # the design variables are the family unit's, as in the PSID
    by_unit = {}
    for person in persons:
        by_unit.setdefault(person.family_unit_id, set()).add(
            (person.stratum, person.cluster)
        )
    assert all(len(pairs) == 1 for pairs in by_unit.values())
    assert sum(person.sex == "unknown" for person in persons) == 1
    assert any(person.unlinked_auxiliary for person in persons)
    assert any(person.other_member for person in persons)
    kinds = {link.kind for person in persons for link in person.links}
    assert kinds == {"spouse", "survivor"}
    assert cohort.provenance_kind == evaluation.INVENTED
    assert cohort.source["label"] == "INVENTED DATA - NOT A COMPARISON"
