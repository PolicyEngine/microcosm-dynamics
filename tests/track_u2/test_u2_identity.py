"""U2 identity and the cross-cohort refusals (section 13, group "Identity").

Wrong cohort, seed, column, rulings, parameters, provenance and artifact
destination refuse; U1's own guards refuse U2's settings; the U1 literals
recorded in :mod:`populace_dynamics.uniform_cut_track_u2.identity` equal
the U1 modules.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u import rows as u1_rows
from populace_dynamics.uniform_cut_track_u import runner as u1_runner
from populace_dynamics.uniform_cut_track_u2 import (
    cohort,
    identity,
    rows,
    runner,
    tabulation,
)

ROOT = Path(__file__).resolve().parents[2]


def test_u1_literals_equal_the_u1_modules():
    block = u1_rows.specification_block()
    assert identity.U1_COMPARATOR_COLUMN == ut.COMPARATOR_COLUMN
    assert identity.U1_STATISTIC_ID == ut.STATISTIC_ID
    assert identity.U1_SPECIFICATION_ID == block["specification"]
    assert identity.U1_SPECIFICATION_PATH == u1_rows.SPECIFICATION_PATH
    assert (
        identity.U1_COMPARATOR_INTERVAL
        == block["comparison"]["comparator_interval"]
    )
    assert identity.U1_THRESHOLDS_SHA256 == ap.THRESHOLDS_SHA256
    assert identity.U1_SSI_SHA256 == ap.SSI_PARAMETERS_SHA256
    assert identity.U1_SEED_WAVE_RULE == age67.Age67Spec().seed_wave_rule
    assert identity.U1_WAVES == age67.WAVES
    assert identity.U1_BIRTH_YEARS == age67.ALL_BIRTH_YEARS
    assert (
        str(identity.U1_ARTIFACT_PATH.relative_to(ROOT))
        == block["entry_points"]["registered_artifact"]
    )


def test_u2_identity_is_separate():
    record = identity.identity()
    assert record["target_id"] == "U2"
    assert record["comparator_column"] == "1946-55"
    assert record["birth_years"] == [1946, 1955]
    assert record["artifact"] == "runs/replication_boomers2004_1946_55_v1.json"
    assert (
        record["sidecar"] == "runs/replication_boomers2004_1946_55_v1.env.json"
    )
    assert record["comparator_interval"].endswith("_open")
    assert tabulation.COMPARATOR_COLUMN != ut.COMPARATOR_COLUMN
    assert tabulation.STATISTIC_ID != ut.STATISTIC_ID
    block = rows.specification_block()
    assert block["target"]["column"] == identity.COMPARATOR_COLUMN
    assert block["entry_points"]["registered_artifact"] == record["artifact"]
    assert block["entry_points"]["environment"] == record["sidecar"]
    assert block["comparison"]["comparator_interval"] == (
        identity.COMPARATOR_INTERVAL
    )


@pytest.mark.parametrize(
    "values",
    [
        {"comparator_column": "1936-45"},
        {"statistic_id": identity.U1_STATISTIC_ID},
        {"specification": "boomers2004_uniform_cut_exercise2"},
        {"thresholds_sha256": identity.U1_THRESHOLDS_SHA256},
        {"ssi_sha256": identity.U1_SSI_SHA256},
        {"seed_wave_rule": "earliest_presence_wave"},
        {"output": "runs/replication_boomers2004_uniform_cut_v1.json"},
        {"output": "runs/replication_boomers2004_uniform_cut_v1.env.json"},
        {"path": "docs/design/boomers2004_uniform_cut_comparison.md"},
    ],
)
def test_u2_refuses_u1_identities(values):
    with pytest.raises(identity.U2IdentityError):
        identity.refuse_u1_identity(values, what="test")


def test_u2_refuses_the_u1_specification_block():
    with pytest.raises(identity.U2IdentityError):
        rows.specification_block(identity.U1_SPECIFICATION_PATH)


def test_u2_refuses_u1_rulings_and_max_rulings():
    decisions = {
        "ruled_by": "Max",
        "ruled_on": "2026-09-26",
        **u1_rows.MAX_RULINGS,
    }
    with pytest.raises(ValueError, match="copying U1"):
        rows.check_u2_rulings_against_block({"decisions": decisions})


def test_draft_block_rulings_are_refused_until_materialized():
    with pytest.raises(ValueError, match="no ruling by Max"):
        rows.check_u2_rulings_against_block(rows.specification_block())
    ruled = {
        "decisions": {
            "ruled_by": "Max",
            "ruled_on": "2026-09-28",
            **rows.U2_RULINGS,
        }
    }
    assert rows.check_u2_rulings_against_block(ruled)["rulings_equal"]
    altered = {"decisions": {**ruled["decisions"], "downloads": {"ruling": 1}}}
    with pytest.raises(ValueError, match="differ"):
        rows.check_u2_rulings_against_block(altered)


def test_u1_guards_refuse_u2_seed_and_rows():
    with pytest.raises(ValueError, match="seed_wave_rule must be"):
        age67.Age67Spec(seed_wave_rule=cohort.SEED_WAVE_RULE)
    with pytest.raises(ValueError):
        age67.Age67Spec(row="U2")
    with pytest.raises(ValueError):
        u1_rows.check_rulings_against_block(
            {
                "decisions": {
                    "ruled_by": "Max",
                    "ruled_on": "2026-09-28",
                    **rows.U2_RULINGS,
                }
            }
        )


def test_u2_seed_refusal_message_is_u1s_unchanged():
    with pytest.raises(ValueError) as error:
        age67.Age67Spec(
            seed_wave_rule="earliest_presence_in_common_support_waves"
        )
    assert str(error.value) == "seed_wave_rule must be earliest_presence_wave"


def test_wrong_target_objects_refuse(u2_inputs):
    import dataclasses

    with pytest.raises(ValueError, match="not 'U2'"):
        dataclasses.replace(u2_inputs, target_id="U1")
    with pytest.raises(ValueError, match="not 'U2'"):
        tabulation.U2TabulationConfig(target_id="U1")
    with pytest.raises(ValueError):
        tabulation.U2TabulationConfig(comparator_column="1936-45")


def test_fixed_headline_refuses_fallback():
    assert runner.check_headline("U0") == "U0"
    for other in ("U0-F", "U1", "U3"):
        with pytest.raises(runner.U2RunError, match="fixed"):
            runner.check_headline(other)


def test_u1_named_deltas_and_rows_are_unchanged():
    assert len(u1_runner.NAMED_DELTAS) == 22
    assert len(u1_rows.REGISTERED_ROWS) == 19
    assert "U0-F" in u1_rows.REGISTERED_ROWS
    assert list(rows.REGISTERED_ROWS) == list(rows.ROW_IDS)


def test_named_deltas_equal_section_12_literally():
    assert rows.check_named_deltas_against_specification() == {
        "n_deltas": 26,
        "equal_to_section_12": True,
    }
    assert all(not delta.endswith(".") for delta in rows.NAMED_DELTAS)
    assert set(rows.NAMED_DELTAS).isdisjoint(u1_runner.NAMED_DELTAS)


def test_rows_equal_the_section_15_block():
    check = rows.check_rows_against_block(rows.specification_block())
    assert check["rows_checked"] == list(rows.ROW_IDS)
    assert check["headline"] == "U0"


def test_block_rows_with_an_omitted_row_refuse():
    block = rows.specification_block()
    block["rows"] = {**block["rows"], "U0-F": {}}
    with pytest.raises(ValueError, match="differ"):
        rows.check_rows_against_block(block)
